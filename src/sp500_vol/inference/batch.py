import logging
from datetime import UTC, date, datetime

import pandas as pd

from sp500_vol.common.baselines import get_forecasts
from sp500_vol.common.bigquery import BigQueryClient
from sp500_vol.common.config import get_git_commit, is_github_actions
from sp500_vol.common.log import github_notice, setup_logging
from sp500_vol.common.registry import CHAMPION, ModelRegistry, RegisteredModel
from sp500_vol.common.schema import DRIFT_TABLE, FEATURES_TABLE, HORIZON, PREDICTIONS_TABLE
from sp500_vol.inference.drift import get_drift

logger = logging.getLogger(__name__)


def get_new_days(features: pd.DataFrame, predicted: set[date], train_end: date) -> pd.DataFrame:
    unseen = features[features["date"] > train_end]
    missing = [day not in predicted for day in unseen["date"]]
    return unseen[missing].sort_values("date")


def get_backfill(days: pd.Series, predicted: set[date]) -> pd.Series:
    first_live = min(predicted) if predicted else days.max()
    return days < first_live


def make_predictions(new_days: pd.DataFrame, champion: RegisteredModel) -> pd.DataFrame:
    forecasts = get_forecasts(new_days, champion.booster, champion.metadata)
    df = pd.concat([new_days[["date", "vix"]], forecasts], axis=1).reset_index(drop=True)
    df["horizon_days"] = HORIZON
    df["model_version"] = champion.version
    df["model_run"] = champion.labels.get("run", "")
    df["git_commit"] = get_git_commit()
    df["predicted_at"] = datetime.now(UTC)
    return df


def make_drift(features: pd.DataFrame, champion: RegisteredModel, train_end: date) -> pd.DataFrame:
    df = get_drift(features, train_end)
    df["date"] = features["date"].max()
    df["model_version"] = champion.version
    df["computed_at"] = datetime.now(UTC)
    return df


def main() -> None:
    bq = BigQueryClient()
    features = bq.read_table(FEATURES_TABLE)
    registry = ModelRegistry()
    champion = registry.load(CHAMPION)
    if champion is None:
        raise RuntimeError("no model, run the training pipeline first")
    train_end = date.fromisoformat(champion.metadata["train_end"])
    predicted = bq.get_dates(PREDICTIONS_TABLE)
    new_days = get_new_days(features, predicted, train_end)
    if new_days.empty:
        github_notice("Inference: no new feature day", [f"Newest day: {features['date'].max()}"])
        return

    predictions = make_predictions(new_days, champion)
    predictions["backfill"] = get_backfill(predictions["date"], predicted)
    drift = make_drift(features, champion, train_end)
    logger.info("predictions:\n%s", predictions.to_string())
    logger.info("drift:\n%s", drift.to_string())

    # local code may not be committed (ADR 2)
    if not is_github_actions():
        logger.info("local run, nothing written")
        return

    bq.append(predictions, PREDICTIONS_TABLE)
    bq.append(drift, DRIFT_TABLE)
    latest = predictions.iloc[-1]
    drifted = drift.loc[drift["psi"] > drift["threshold"], "feature"].tolist()
    github_notice(
        "Inference: new forecast",
        [
            f"Day: {latest['date']}",
            f"Forecast: {latest['model']:.1f}, HAR-RV {latest['har_rv']:.1f}",
            f"Model version: {champion.version}",
            f"New days: {len(predictions)}, backfill {predictions['backfill'].sum()}",
            f"PSI above threshold: {', '.join(drifted) or 'none'}",
        ],
    )


if __name__ == "__main__":
    setup_logging()
    main()
