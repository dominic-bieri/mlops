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
from sp500_vol.evaluation.baselines import HAR_COLUMNS, fit_har, get_cutoff, split
from sp500_vol.features.build import FEATURE_COLUMNS, LABEL_COLUMN

logger = logging.getLogger(__name__)

MODEL_NAME = "sp500-vol"
# registry needs an image, inference runs on Cloud Run (ADR 1)
SERVING_IMAGE = "us-docker.pkg.dev/cloudrun/container/placeholder:latest"


def fit_model(train: pd.DataFrame, val: pd.DataFrame) -> lgb.LGBMRegressor:
    model = lgb.LGBMRegressor(
        objective="l1",
        learning_rate=0.02,
        n_estimators=2000,
        random_state=42,
        deterministic=True,
        force_row_wise=True,
        verbose=-1,
    )

    # number of trees chosen on val
    stop = lgb.early_stopping(50, verbose=False)
    model.fit(
        train[FEATURE_COLUMNS],
        train[LABEL_COLUMN],
        eval_X=val[FEATURE_COLUMNS],
        eval_y=val[LABEL_COLUMN],
        eval_metric="l1",
        callbacks=[stop],
    )
    return model


def register_model(model: lgb.LGBMRegressor, run_name: str) -> str:
    joblib.dump(model, "model.joblib")
    bucket = storage.Client().bucket(get_model_bucket())
    bucket.blob(f"{run_name}/model.joblib").upload_from_filename("model.joblib")

    # new version of the same model, becomes the default
    parent = None
    existing = aiplatform.Model.list(filter=f'display_name="{MODEL_NAME}"')
    if existing:
        parent = existing[0].resource_name

    registered = aiplatform.Model.upload(
        display_name=MODEL_NAME,
        artifact_uri=f"gs://{get_model_bucket()}/{run_name}",
        serving_container_image_uri=SERVING_IMAGE,
        parent_model=parent,
        labels={"run": run_name},
    )
    return registered.version_id


def log_run(run_name: str, params: dict, metrics: dict) -> None:
    aiplatform.start_run(run_name)
    aiplatform.log_params(params)
    aiplatform.log_metrics(metrics)
    aiplatform.end_run()


def main() -> None:
    bq = BigQueryClient()
    snapshot = bq.get_latest_snapshot("features_")
    features = bq.read_table(snapshot)

    cutoff = get_cutoff(features)
    train, val, test = split(features, cutoff)

    model = fit_model(train, val)
    har = fit_har(train)

    val_prediction = model.predict(val[FEATURE_COLUMNS])
    test_prediction = model.predict(test[FEATURE_COLUMNS])
    har_prediction = har.predict(test[HAR_COLUMNS])

    val_mae = mean_absolute_error(val[LABEL_COLUMN], val_prediction)
    test_mae = mean_absolute_error(test[LABEL_COLUMN], test_prediction)
    har_mae = mean_absolute_error(test[LABEL_COLUMN], har_prediction)
    logger.info("test mae: model %.2f, har_rv %.2f", test_mae, har_mae)

    aiplatform.init(
        project=get_gcp_project_id(),
        location=get_gcp_region(),
        experiment=MODEL_NAME,
        experiment_tensorboard=False,
    )
    run_name = datetime.now(UTC).strftime("run-%Y%m%d-%H%M%S")

    # only a model that beats HAR-RV is registered (ADR 9)
    model_version = "none"
    if test_mae < har_mae:
        model_version = register_model(model, run_name)
    logger.info("run: %s, model version: %s", run_name, model_version)

    params = {
        "snapshot": snapshot,
        "git_commit": get_git_commit(),
        "cutoff": str(cutoff),
        "trees": model.best_iteration_,
        "learning_rate": model.learning_rate,
        "num_leaves": model.num_leaves,
        "min_child_samples": model.min_child_samples,
        "model_version": model_version,
    }
    metrics = {
        "val_mae": val_mae,
        "test_mae": test_mae,
        "har_rv_test_mae": har_mae,
    }
    log_run(run_name, params, metrics)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
