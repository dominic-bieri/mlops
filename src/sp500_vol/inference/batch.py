import logging
from datetime import UTC, date, datetime

import lightgbm as lgb
import pandas as pd

from sp500_vol.common.bigquery import BigQueryClient
from sp500_vol.common.config import (
    get_git_commit,
    github_notice,
    is_github_actions,
    setup_logging,
)
from sp500_vol.common.registry import (
    CHAMPION,
    RegisteredModel,
    load_booster,
    load_registered_model,
)
from sp500_vol.inference.drift import get_drift
from sp500_vol.inference.predict import get_backfill, get_new_days, predict

logger = logging.getLogger(__name__)


def make_predictions(
    new_days: pd.DataFrame, champion: RegisteredModel, booster: lgb.Booster
) -> pd.DataFrame:
    df = predict(new_days, booster, champion.metadata)
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
    features = bq.read_table("features")
    champion = load_registered_model(CHAMPION)
    train_end = date.fromisoformat(champion.metadata["train_end"])
    predicted = bq.get_dates("predictions")
    new_days = get_new_days(features, predicted, train_end)
    if new_days.empty:
        github_notice("Inference: no new feature day", [f"Newest day: {features['date'].max()}"])
        return

    # by version id, the alias may move in between
    booster = load_booster(champion.version)
    predictions = make_predictions(new_days, champion, booster)
    predictions["backfill"] = get_backfill(predictions["date"], predicted)
    drift = make_drift(features, champion, train_end)
    logger.info("predictions:\n%s", predictions.to_string())
    logger.info("drift:\n%s", drift.to_string())

    # local code may not be committed (ADR 2)
    if not is_github_actions():
        logger.info("local run, nothing written")
        return

    bq.append(predictions, "predictions")
    bq.append(drift, "drift")
    latest = predictions.iloc[-1]
    drifted = drift.loc[drift["psi"] > drift["threshold"], "feature"].tolist()
    github_notice(
        "Inference: new forecast",
        [
            f"Day: {latest['date']}",
            f"Forecast: {latest['prediction']:.1f}, HAR-RV {latest['har_rv']:.1f}",
            f"Model version: {champion.version}",
            f"New days: {len(predictions)}, backfill {predictions['backfill'].sum()}",
            f"PSI above threshold: {', '.join(drifted) or 'none'}",
        ],
    )


if __name__ == "__main__":
    setup_logging()
    main()
