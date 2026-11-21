import logging
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from sp500_vol.common.bigquery import BigQueryClient
from sp500_vol.common.config import get_git_commit, is_github_actions
from sp500_vol.common.log import github_summary, github_warning, setup_logging
from sp500_vol.common.schema import (
    FEATURE_COLUMNS,
    FEATURES_TABLE,
    HORIZON,
    LABEL_COLUMN,
    NEW_YORK,
    SNAPSHOT_PREFIX,
    SP500_TABLE,
    VIX_TABLE,
)
from sp500_vol.features.snapshots import delete_unused_snapshots
from sp500_vol.features.validate import check_freshness, validate_features

logger = logging.getLogger(__name__)

TRADING_DAYS_PER_YEAR = 252
RV_WINDOWS = [1, 5, 10, 20, 22, 60]
VIX_CHANGE_DAYS = 5


# Garman-Klass-Yang-Zhang, formula in ADR 3
def daily_variance(df: pd.DataFrame) -> pd.Series:
    previous_close = df["close"].shift(1)
    overnight = np.log((df["open"] + df["div_cash"]) / previous_close)
    high_low = np.log(df["high"] / df["low"])
    open_close = np.log(df["close"] / df["open"])
    return overnight**2 + 0.5 * high_low**2 - (2 * np.log(2) - 1) * open_close**2


# percent per year, like the VIX
def realized_vol(daily_var: pd.Series, window: int) -> pd.Series:
    mean_var = daily_var.rolling(window).mean()
    return np.sqrt(mean_var * TRADING_DAYS_PER_YEAR) * 100


def build_spy_features(sp500: pd.DataFrame) -> pd.DataFrame:
    df = sp500.sort_values("date").reset_index(drop=True)

    # dividend added back (ADR 1)
    previous_close = df["close"].shift(1)
    df["log_return"] = np.log((df["close"] + df["div_cash"]) / previous_close)
    df["abs_log_return"] = df["log_return"].abs()

    daily_var = daily_variance(df)
    for window in RV_WINDOWS:
        df[f"rv_{window}d"] = realized_vol(daily_var, window)

    # value at t+5 covers t+1..t+5
    df[LABEL_COLUMN] = df[f"rv_{HORIZON}d"].shift(-HORIZON)
    return df


def build_vix_features(vix: pd.DataFrame, trading_days: pd.Series) -> pd.DataFrame:
    df = pd.DataFrame({"date": trading_days})
    df = df.merge(vix[["date", "close"]], on="date", how="left")
    df = df.rename(columns={"close": "vix"})
    df["vix_change_5d"] = df["vix"] - df["vix"].shift(VIX_CHANGE_DAYS)
    return df


def build_features(sp500: pd.DataFrame, vix: pd.DataFrame) -> pd.DataFrame:
    spy_features = build_spy_features(sp500)
    vix_features = build_vix_features(vix, spy_features["date"])

    df = spy_features.merge(vix_features, on="date", how="left")

    df = df.dropna(subset=FEATURE_COLUMNS)

    columns = ["date"] + FEATURE_COLUMNS + [LABEL_COLUMN]
    return df[columns].reset_index(drop=True)


def clean_up_snapshots(bq: BigQueryClient) -> list[str]:
    try:
        return delete_unused_snapshots(bq)
    except Exception as e:
        logger.exception("snapshot cleanup failed")
        github_warning("Features: snapshot cleanup failed", type(e).__name__)
        return []


def get_snapshot_name(built_at: datetime) -> str:
    return SNAPSHOT_PREFIX + built_at.strftime("%Y%m%d_%H%M%S")


def main() -> None:
    bq = BigQueryClient()

    sp500 = bq.read_table(SP500_TABLE)
    vix = bq.read_table(VIX_TABLE)
    features = build_features(sp500, vix)
    logger.info("features: %d rows", len(features))

    if not is_github_actions():
        logger.info("local run, nothing written")
        return

    validate_features(features, datetime.now(UTC).date())
    bq.replace_all(features, FEATURES_TABLE)
    snapshot = get_snapshot_name(datetime.now(UTC))
    bq.create_snapshot(FEATURES_TABLE, snapshot, f"commit {get_git_commit()}")
    deleted = clean_up_snapshots(bq)
    newest = features["date"].max()
    github_summary(
        "Features: new snapshot",
        [
            f"Snapshot: {snapshot}",
            f"Rows: {len(features)}",
            f"Newest day: {newest}",
            f"Deleted snapshots: {', '.join(deleted) or 'none'}",
        ],
    )
    check_freshness(newest, datetime.now(NEW_YORK).date())


if __name__ == "__main__":
    setup_logging()
    main()
