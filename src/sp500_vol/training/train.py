import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import lightgbm as lgb
import pandas as pd
from google.cloud import aiplatform
from sklearn.metrics import mean_absolute_error

from sp500_vol.common.bigquery import BigQueryClient
from sp500_vol.common.config import (
    get_gcp_project_id,
    get_gcp_region,
    get_git_commit,
    is_github_actions,
    setup_logging,
)
from sp500_vol.features.build import FEATURE_COLUMNS, LABEL_COLUMN, SNAPSHOT_PREFIX
from sp500_vol.training.evaluate import get_errors, get_errors_by_year
from sp500_vol.training.model import fit_model, refit_model
from sp500_vol.training.registry import MODEL_NAME, ModelRegistry
from sp500_vol.training.split import get_cutoff, split

logger = logging.getLogger(__name__)

MAX_MODEL_AGE = timedelta(days=180)


@dataclass
class TrainingResult:
    model: lgb.LGBMRegressor
    params: dict
    metrics: dict
    test: pd.DataFrame


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


def train_and_evaluate(features: pd.DataFrame, snapshot: str) -> TrainingResult:
    cutoff = get_cutoff(features)
    train, val, test = split(features, cutoff)

    # fitted on train, val only chooses the trees (ADR 7)
    tuned = fit_model(train, val)
    unseen = pd.concat([val, test])
    errors_by_year = get_errors_by_year(tuned, train, unseen)
    logger.info("mae per year:\n%s", errors_by_year.to_string())

    train_val = pd.concat([train, val])
    model = refit_model(train_val, tuned.best_iteration_)
    errors = get_errors(model, train_val, test)
    metrics = {
        "test_mae": errors["model"].mean(),
        "rv_20d_test_mae": errors["rv_20d"].mean(),
        "har_rv_test_mae": errors["har_rv"].mean(),
        "vix_scaled_test_mae": errors["vix_scaled"].mean(),
    }
    params = {
        "snapshot": snapshot,
        "git_commit": get_git_commit(),
        "cutoff": str(cutoff),
        "trees": tuned.best_iteration_,
        "learning_rate": model.learning_rate,
        "num_leaves": model.num_leaves,
        "min_child_samples": model.min_child_samples,
    }
    logger.info("metrics: %s", metrics)
    return TrainingResult(model, params, metrics, test)


def track_and_register(result: TrainingResult) -> None:
    aiplatform.init(
        project=get_gcp_project_id(),
        location=get_gcp_region(),
        experiment=MODEL_NAME,
        experiment_tensorboard=False,
    )
    registry = ModelRegistry()
    run_name = datetime.now(UTC).strftime("run-%Y%m%d-%H%M%S")

    with aiplatform.start_run(run_name):
        aiplatform.log_params(result.params)
        aiplatform.log_metrics(result.metrics)

        best_mae = result.metrics["har_rv_test_mae"]
        parent = registry.get_parent()
        current = registry.get_champion(parent)
        if current is not None:
            current_mae = get_current_mae(registry, current, result.test)
            if current_mae is None:
                logger.info("current model not comparable, only HAR-RV counts")
            else:
                aiplatform.log_metrics({"current_test_mae": current_mae})
                best_mae = min(best_mae, current_mae)

        test_mae = result.metrics["test_mae"]
        model_version = "none"
        if test_mae < best_mae:
            params = result.params
            description = (
                f"run {run_name}, commit {params['git_commit']}, snapshot {params['snapshot']}"
            )
            model_version = registry.register(result.model, run_name, parent, description)
        aiplatform.log_params({"model_version": model_version})

    logger.info("test mae: model %.2f, to beat %.2f", test_mae, best_mae)
    logger.info("run: %s, model version: %s", run_name, model_version)


def main() -> None:
    bq = BigQueryClient()
    snapshot = bq.get_latest_snapshot(SNAPSHOT_PREFIX)
    features = bq.read_table(snapshot)
    result = train_and_evaluate(features, snapshot)

    # local code may not be committed (ADR 10)
    if not is_github_actions():
        logger.info("local run, nothing logged or registered")
        return
    track_and_register(result)


if __name__ == "__main__":
    setup_logging()
    main()
