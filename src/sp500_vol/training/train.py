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
    get_image,
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
ERRORS_FILE = "errors_by_year.csv"
ERRORS_DIR = "errors"


@dataclass
class TrainingResult:
    model: lgb.LGBMRegressor
    params: dict
    metrics: dict
    test: pd.DataFrame
    errors_by_year: pd.DataFrame


def get_current_mae(
    registry: ModelRegistry, current: aiplatform.Model | None, test: pd.DataFrame
) -> float | None:
    if current is None:
        logger.info("no current model, only HAR-RV counts")
        return None
    age = datetime.now(UTC) - current.version_create_time
    if age > MAX_MODEL_AGE:
        logger.info("current model is %d days old, only HAR-RV counts", age.days)
        return None

    booster = registry.load_model(current)
    if booster.feature_name() != FEATURE_COLUMNS:
        logger.info("current model has other features, only HAR-RV counts")
        return None

    prediction = booster.predict(test[FEATURE_COLUMNS])
    return mean_absolute_error(test[LABEL_COLUMN], prediction)


def should_register(test_mae: float, har_mae: float, current_mae: float | None) -> bool:
    if test_mae >= har_mae:
        return False
    if current_mae is None:
        return True
    return test_mae <= current_mae


def get_windows(train: pd.DataFrame, val: pd.DataFrame, test: pd.DataFrame) -> dict:
    windows: dict[str, str | int] = {}
    for name, df in [("train", train), ("val", val), ("test", test)]:
        windows[f"{name}_start"] = str(df["date"].min())
        windows[f"{name}_end"] = str(df["date"].max())
        windows[f"{name}_rows"] = len(df)
    return windows


def train_and_evaluate(features: pd.DataFrame, snapshot: str) -> TrainingResult:
    cutoff = get_cutoff(features)
    train, val, test = split(features, cutoff)

    # fitted on train, val only chooses the trees (ADR 4)
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
        "image": get_image(),
        "cutoff": str(cutoff),
        **get_windows(train, val, test),
        "features": ",".join(FEATURE_COLUMNS),
        "trees": tuned.best_iteration_,
        "learning_rate": model.learning_rate,
        "num_leaves": model.num_leaves,
        "min_child_samples": model.min_child_samples,
    }
    logger.info("metrics: %s", {key: round(float(value), 4) for key, value in metrics.items()})
    return TrainingResult(model, params, metrics, test, errors_by_year)


def track_and_register(result: TrainingResult) -> None:
    aiplatform.init(
        project=get_gcp_project_id(),
        location=get_gcp_region(),
        experiment=MODEL_NAME,
        experiment_tensorboard=False,
    )
    registry = ModelRegistry()
    run_name = datetime.now(UTC).strftime("run-%Y%m%d-%H%M%S")
    params = result.params
    metrics = result.metrics
    test_mae = metrics["test_mae"]
    har_mae = metrics["har_rv_test_mae"]

    parent = registry.get_parent()
    current = registry.get_champion(parent)
    current_mae = get_current_mae(registry, current, result.test)

    with aiplatform.start_run(run_name):
        # not in the model folder, comes from the model fitted on train only
        errors_path = f"{ERRORS_DIR}/{run_name}/{ERRORS_FILE}"
        errors_uri = registry.upload(errors_path, result.errors_by_year.to_csv())
        aiplatform.log_params({**params, "errors_by_year": errors_uri})
        aiplatform.log_metrics(metrics)
        if current_mae is not None:
            aiplatform.log_metrics({"current_test_mae": current_mae})

        model_version: str | None = None
        if should_register(test_mae, har_mae, current_mae):
            description = (
                f"run {run_name}, commit {params['git_commit']}, snapshot {params['snapshot']}, "
                f"test MAE {test_mae:.4f}, HAR-RV {har_mae:.4f}"
            )
            labels = {
                "run": run_name,
                "git_commit": params["git_commit"],
                "snapshot": params["snapshot"],
            }
            model_version = registry.register(result.model, run_name, parent, description, labels)
        aiplatform.log_params({"model_version": model_version or "none"})

    current_text = "none" if current_mae is None else f"{current_mae:.4f}"
    registered = "not registered" if model_version is None else f"version {model_version}"
    logger.info(
        "run %s, %s, test MAE %.4f, HAR-RV %.4f, current %s",
        run_name,
        registered,
        test_mae,
        har_mae,
        current_text,
    )


def main() -> None:
    bq = BigQueryClient()
    snapshot = bq.get_latest_snapshot(SNAPSHOT_PREFIX)
    features = bq.read_table(snapshot)
    result = train_and_evaluate(features, snapshot)

    # local code may not be committed (ADR 2)
    if not is_github_actions():
        logger.info("local run, nothing logged or registered")
        return
    track_and_register(result)


if __name__ == "__main__":
    setup_logging()
    main()
