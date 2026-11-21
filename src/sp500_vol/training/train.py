import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import lightgbm as lgb
import numpy as np
import pandas as pd
from google.cloud import aiplatform
from sklearn.metrics import mean_absolute_error

from sp500_vol.common.baselines import get_baselines, get_forecasts
from sp500_vol.common.bigquery import BigQueryClient
from sp500_vol.common.config import get_git_commit, get_image, is_github_actions
from sp500_vol.common.log import github_summary, github_table, setup_logging
from sp500_vol.common.registry import CHAMPION, MODEL_NAME, ModelRegistry, RegisteredModel
from sp500_vol.common.schema import FEATURE_COLUMNS, LABEL_COLUMN, SNAPSHOT_PREFIX
from sp500_vol.training.model import fit_model, refit_model, split

logger = logging.getLogger(__name__)

MAX_MODEL_AGE = timedelta(days=180)
VIX_STRESSED = 20


@dataclass
class TrainingResult:
    model: lgb.LGBMRegressor
    params: dict
    test: pd.DataFrame
    metadata: dict
    errors_by_year: pd.DataFrame


def get_errors(df: pd.DataFrame, booster: lgb.Booster, baselines: dict) -> pd.DataFrame:
    return get_forecasts(df, booster, baselines).sub(df[LABEL_COLUMN], axis=0).abs()


def get_errors_by_year(
    df: pd.DataFrame, booster: lgb.Booster, baselines: dict, split_name: str
) -> pd.DataFrame:
    errors = get_errors(df, booster, baselines)
    errors["split"] = split_name
    errors["year"] = pd.to_datetime(df["date"]).dt.year
    errors["days"] = np.where(df["vix"] > VIX_STRESSED, "stressed", "calm")
    groups = errors.groupby(["split", "year", "days"])
    table = groups.mean().round(2)
    table["n"] = groups.size()
    return table.reset_index()


def get_current_mae(current: RegisteredModel | None, test: pd.DataFrame) -> float | None:
    if current is None:
        logger.info("no current model, only HAR-RV counts")
        return None
    age = datetime.now(UTC) - current.created
    if age > MAX_MODEL_AGE:
        logger.info("current model is %d days old, only HAR-RV counts", age.days)
        return None
    prediction = current.booster.predict(test[FEATURE_COLUMNS])
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
    train, val, test = split(features)

    # fitted on train, val only chooses the trees (ADR 4)
    tuned = fit_model(train, val)
    val_errors = get_errors_by_year(val, tuned.booster_, get_baselines(train), "val")

    train_val = pd.concat([train, val])
    model = refit_model(train_val, tuned.best_iteration_)
    baselines = get_baselines(train_val)
    errors = get_errors(test, model.booster_, baselines)
    test_errors = get_errors_by_year(test, model.booster_, baselines, "test")
    errors_by_year = pd.concat([val_errors, test_errors], ignore_index=True)
    logger.info("mae per year:\n%s", errors_by_year.to_string(index=False))
    params = {
        "snapshot": snapshot,
        "git_commit": get_git_commit(),
        "image": get_image(),
        **get_windows(train, val, test),
        "features": ",".join(FEATURE_COLUMNS),
        "trees": tuned.best_iteration_,
        "learning_rate": model.learning_rate,
        "num_leaves": model.num_leaves,
        "min_child_samples": model.min_child_samples,
    }
    train_end = str(train_val["date"].max())
    metadata = {"train_end": train_end, "test_mae": errors.mean().to_dict(), **baselines}
    logger.info(
        "test mae: %s", {key: round(value, 4) for key, value in metadata["test_mae"].items()}
    )
    return TrainingResult(model, params, test, metadata, errors_by_year)


def register(registry: ModelRegistry, result: TrainingResult, run_name: str) -> str:
    params = result.params
    test_mae = result.metadata["test_mae"]["model"]
    har_mae = result.metadata["test_mae"]["har_rv"]
    description = (
        f"run {run_name}, commit {params['git_commit']}, snapshot {params['snapshot']}, "
        f"test MAE {test_mae:.4f}, HAR-RV {har_mae:.4f}"
    )
    labels = {
        "run": run_name,
        "git_commit": params["git_commit"],
        "snapshot": params["snapshot"],
    }
    return registry.register(result.model, result.metadata, run_name, description, labels)


def notify(
    result: TrainingResult, run_name: str, current_mae: float | None, model_version: str | None
) -> None:
    test_mae = result.metadata["test_mae"]["model"]
    har_mae = result.metadata["test_mae"]["har_rv"]
    current_text = "none" if current_mae is None else f"{current_mae:.4f}"
    details = [
        f"Test MAE: model {test_mae:.4f}, HAR-RV {har_mae:.4f}, champion {current_text}",
        f"Run: {run_name}",
        f"Snapshot: {result.params['snapshot']}",
    ]
    if model_version is None:
        github_summary("Training: no new model", ["Champion unchanged", *details])
    else:
        github_summary(
            "Training: new model registered", [f"Version {model_version} is champion", *details]
        )
    github_table(f"MAE per year, stressed: VIX above {VIX_STRESSED}", result.errors_by_year)


def track_and_register(result: TrainingResult) -> None:
    # sets project and region
    registry = ModelRegistry()
    aiplatform.init(experiment=MODEL_NAME, experiment_tensorboard=False)
    run_name = datetime.now(UTC).strftime("run-%Y%m%d-%H%M%S")
    test_mae = result.metadata["test_mae"]

    current_mae = get_current_mae(registry.load(CHAMPION), result.test)

    with aiplatform.start_run(run_name):
        aiplatform.log_params(result.params)
        aiplatform.log_metrics({f"{name}_test_mae": mae for name, mae in test_mae.items()})
        if current_mae is not None:
            aiplatform.log_metrics({"current_test_mae": current_mae})

        model_version: str | None = None
        if should_register(test_mae["model"], test_mae["har_rv"], current_mae):
            model_version = register(registry, result, run_name)
        aiplatform.log_params({"model_version": model_version or "none"})

    notify(result, run_name, current_mae, model_version)


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
