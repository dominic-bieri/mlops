import logging
from datetime import UTC, date, datetime

import pandas as pd

from sp500_vol.common.bigquery import BigQueryClient
from sp500_vol.common.config import (
    get_git_commit,
    github_notice,
    is_github_actions,
    setup_logging,
)
from sp500_vol.inference.drift import PSI_WARNING, get_drift
from sp500_vol.inference.model import Champion, load_champion
from sp500_vol.inference.predict import get_new_days, predict

logger = logging.getLogger(__name__)


def make_predictions(new_days: pd.DataFrame, champion: Champion) -> pd.DataFrame:
    df = predict(new_days, champion.booster, champion.metadata)
    df["model_version"] = champion.version
    df["model_run"] = champion.labels.get("run", "")
    df["git_commit"] = get_git_commit()
    df["predicted_at"] = datetime.now(UTC)
    return df


def make_drift(features: pd.DataFrame, champion: Champion) -> pd.DataFrame:
    train_end = date.fromisoformat(champion.metadata["train_end"])
    df = get_drift(features, train_end)
    df["date"] = features["date"].max()
    df["model_version"] = champion.version
    df["computed_at"] = datetime.now(UTC)
    return df


def main() -> None:
    bq = BigQueryClient()
    features = bq.read_table("features")
    new_days = get_new_days(features, bq.get_dates("predictions"))
    if new_days.empty:
        github_notice("Inference: no new feature day", [f"Newest day: {features['date'].max()}"])
        return

    champion = load_champion()
    predictions = make_predictions(new_days, champion)
    drift = make_drift(features, champion)
    logger.info("predictions:\n%s", predictions.to_string())
    logger.info("drift:\n%s", drift.to_string())

    # local code may not be committed (ADR 2)
    if not is_github_actions():
        logger.info("local run, nothing written")
        return

    bq.append(predictions, "predictions")
    bq.append(drift, "drift")
    latest = predictions.iloc[-1]
    drifted = drift.loc[drift["psi"] > PSI_WARNING, "feature"].tolist()
    github_notice(
        "Inference: new forecast",
        [
            f"Day: {latest['date']}",
            f"Forecast: {latest['prediction']:.1f}, HAR-RV {latest['har_rv']:.1f}",
            f"Model version: {champion.version}",
            f"New days: {len(predictions)}",
            f"PSI > {PSI_WARNING}: {', '.join(drifted) or 'none'}",
        ],
    )


if __name__ == "__main__":
    setup_logging()
    main()
