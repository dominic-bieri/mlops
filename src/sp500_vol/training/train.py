import logging
from datetime import UTC, datetime

import joblib
import lightgbm as lgb
import pandas as pd
from google.cloud import aiplatform, storage
from sklearn.metrics import mean_absolute_error

from sp500_vol.common.bigquery import BigQueryClient
from sp500_vol.common.config import (
    get_gcp_project_id,
    get_gcp_region,
    get_git_commit,
    get_model_bucket,
)
from sp500_vol.evaluation.baselines import fit_har, get_cutoff, get_errors, get_vix_factor, split
from sp500_vol.features.build import FEATURE_COLUMNS, LABEL_COLUMN, SNAPSHOT_PREFIX
from sp500_vol.training.model import fit_model, refit_model

logger = logging.getLogger(__name__)

MODEL_NAME = "sp500-vol"
# registry needs an image, inference runs on Cloud Run (ADR 1)
SERVING_IMAGE = "us-docker.pkg.dev/cloudrun/container/placeholder:latest"
MODEL_FILE = "model.joblib"


# the default version, None before the first registration
def get_current_model() -> aiplatform.Model | None:
    existing = aiplatform.Model.list(filter=f'display_name="{MODEL_NAME}"')
    if len(existing) > 1:
        raise ValueError(f"{len(existing)} models named {MODEL_NAME}, keep only one")
    if existing:
        return existing[0]
    return None


def get_blob(run_name: str) -> storage.Blob:
    client = storage.Client(project=get_gcp_project_id())
    bucket = client.bucket(get_model_bucket())
    return bucket.blob(f"{run_name}/{MODEL_FILE}")


def load_model(registered: aiplatform.Model) -> lgb.LGBMRegressor:
    blob = get_blob(registered.labels["run"])
    with blob.open("rb") as file:
        return joblib.load(file)


def get_current_mae(current: aiplatform.Model, test: pd.DataFrame) -> float | None:
    current_model = load_model(current)
    # an old model with other features can't be compared
    if current_model.feature_name_ != FEATURE_COLUMNS:
        return None
    prediction = current_model.predict(test[FEATURE_COLUMNS])
    return mean_absolute_error(test[LABEL_COLUMN], prediction)


def register_model(model: lgb.LGBMRegressor, run_name: str, parent: str | None) -> str:
    # written straight to the bucket, no local file
    blob = get_blob(run_name)
    with blob.open("wb") as file:
        joblib.dump(model, file)

    # new version of the same model, becomes the default
    registered = aiplatform.Model.upload(
        display_name=MODEL_NAME,
        artifact_uri=f"gs://{get_model_bucket()}/{run_name}",
        serving_container_image_uri=SERVING_IMAGE,
        parent_model=parent,
        labels={"run": run_name},
    )
    return registered.version_id


def main() -> None:
    bq = BigQueryClient()
    snapshot = bq.get_latest_snapshot(SNAPSHOT_PREFIX)
    features = bq.read_table(snapshot)

    cutoff = get_cutoff(features)
    train, val, test = split(features, cutoff)

    # trees chosen on val, then trained again on train and val (ADR 9)
    tuned = fit_model(train, val)
    train_val = pd.concat([train, val])
    model = refit_model(train_val, tuned.best_iteration_)

    # baselines fitted on the same data as the model (ADR 7)
    har = fit_har(train_val)
    vix_factor = get_vix_factor(train_val)
    errors = get_errors(test, model, har, vix_factor)

    aiplatform.init(
        project=get_gcp_project_id(),
        location=get_gcp_region(),
        experiment=MODEL_NAME,
        experiment_tensorboard=False,
    )
    run_name = datetime.now(UTC).strftime("run-%Y%m%d-%H%M%S")

    params = {
        "snapshot": snapshot,
        "git_commit": get_git_commit(),
        "cutoff": str(cutoff),
        "trees": tuned.best_iteration_,
        "learning_rate": model.learning_rate,
        "num_leaves": model.num_leaves,
        "min_child_samples": model.min_child_samples,
    }
    val_prediction = tuned.predict(val[FEATURE_COLUMNS])
    metrics = {
        "val_mae": mean_absolute_error(val[LABEL_COLUMN], val_prediction),
        "test_mae": errors["model"].mean(),
        "rv_20d_test_mae": errors["rv_20d"].mean(),
        "har_rv_test_mae": errors["har_rv"].mean(),
        "vix_scaled_test_mae": errors["vix_scaled"].mean(),
    }

    # run is logged first, so it exists even if the upload fails
    with aiplatform.start_run(run_name):
        aiplatform.log_params(params)
        aiplatform.log_metrics(metrics)

        # must beat HAR-RV and the current default model (ADR 9)
        best_mae = metrics["har_rv_test_mae"]
        current = get_current_model()
        parent = None
        if current is not None:
            parent = current.resource_name
            current_mae = get_current_mae(current, test)
            if current_mae is not None:
                aiplatform.log_metrics({"current_test_mae": current_mae})
                best_mae = min(best_mae, current_mae)

        model_version = "none"
        if metrics["test_mae"] < best_mae:
            model_version = register_model(model, run_name, parent)
        aiplatform.log_params({"model_version": model_version})

    logger.info("test mae: model %.2f, to beat %.2f", metrics["test_mae"], best_mae)
    logger.info("run: %s, model version: %s", run_name, model_version)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
