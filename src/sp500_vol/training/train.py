import logging
from datetime import UTC, datetime, timedelta

import pandas as pd
from google.cloud import aiplatform
from sklearn.metrics import mean_absolute_error

from sp500_vol.common.bigquery import BigQueryClient
from sp500_vol.common.config import get_gcp_project_id, get_gcp_region, get_git_commit
from sp500_vol.features.build import FEATURE_COLUMNS, LABEL_COLUMN, SNAPSHOT_PREFIX
from sp500_vol.training.baselines import get_errors, get_errors_by_year
from sp500_vol.training.model import fit_model, refit_model
from sp500_vol.training.registry import MODEL_NAME, ModelRegistry
from sp500_vol.training.split import get_cutoff, split

logger = logging.getLogger(__name__)

MAX_MODEL_AGE = timedelta(days=180)


def get_current_mae(
    registry: ModelRegistry, current: aiplatform.Model, test: pd.DataFrame
) -> float | None:
    age = datetime.now(UTC) - current.version_create_time
    if age > MAX_MODEL_AGE:
        return None

    booster = registry.load_model(current)
    if booster is None:
        return None
    if booster.feature_name() != FEATURE_COLUMNS:
        return None

    prediction = booster.predict(test[FEATURE_COLUMNS])
    return mean_absolute_error(test[LABEL_COLUMN], prediction)


def main() -> None:
    bq = BigQueryClient()
    snapshot = bq.get_latest_snapshot(SNAPSHOT_PREFIX)
    features = bq.read_table(snapshot)

    cutoff = get_cutoff(features)
    train, val, test = split(features, cutoff)

    # fitted on train only, so val and test are unseen (ADR 7)
    tuned = fit_model(train, val)
    unseen = pd.concat([val, test])
    errors_by_year = get_errors_by_year(tuned, train, unseen)
    logger.info("mae per year:\n%s", errors_by_year.to_string())

    train_val = pd.concat([train, val])
    model = refit_model(train_val, tuned.best_iteration_)
    errors = get_errors(model, train_val, test)

    registry = ModelRegistry()
    run_name = datetime.now(UTC).strftime("run-%Y%m%d-%H%M%S")
    registry.save_file(run_name, "errors_by_year.csv", errors_by_year.to_csv())

    aiplatform.init(
        project=get_gcp_project_id(),
        location=get_gcp_region(),
        experiment=MODEL_NAME,
        experiment_tensorboard=False,
    )
    params = {
        "snapshot": snapshot,
        "git_commit": get_git_commit(),
        "cutoff": str(cutoff),
        "trees": tuned.best_iteration_,
        "learning_rate": model.learning_rate,
        "num_leaves": model.num_leaves,
        "min_child_samples": model.min_child_samples,
    }
    metrics = {
        "test_mae": errors["model"].mean(),
        "rv_20d_test_mae": errors["rv_20d"].mean(),
        "har_rv_test_mae": errors["har_rv"].mean(),
        "vix_scaled_test_mae": errors["vix_scaled"].mean(),
    }

    # run is logged first, so it exists even if the upload fails
    with aiplatform.start_run(run_name):
        aiplatform.log_params(params)
        aiplatform.log_metrics(metrics)

        best_mae = metrics["har_rv_test_mae"]
        current = registry.get_current_model()
        parent = None
        if current is not None:
            parent = current.resource_name
            current_mae = get_current_mae(registry, current, test)
            if current_mae is not None:
                aiplatform.log_metrics({"current_test_mae": current_mae})
                best_mae = min(best_mae, current_mae)

        model_version = "none"
        if metrics["test_mae"] < best_mae:
            model_version = registry.register(model, run_name, parent)
        aiplatform.log_params({"model_version": model_version})

    logger.info("test mae: model %.2f, to beat %.2f", metrics["test_mae"], best_mae)
    logger.info("run: %s, model version: %s", run_name, model_version)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
