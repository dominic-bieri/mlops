import logging
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from sp500_vol.common.bigquery import BigQueryClient
from sp500_vol.common.config import get_git_commit

logger = logging.getLogger(__name__)

TRADING_DAYS_PER_YEAR = 252
RV_WINDOWS = [1, 5, 10, 20, 22, 60]
HORIZON = 5
VIX_CHANGE_DAYS = 5

FEATURE_COLUMNS = [
    "log_return",
    "abs_log_return",
    "rv_1d",
    "rv_5d",
    "rv_10d",
    "rv_20d",
    "rv_22d",
    "rv_60d",
    "vix",
    "vix_change_5d",
]
LABEL_COLUMN = "rv_next_5d"


# Garman-Klass-Yang-Zhang, formula in ADR 6
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

    # dividend added back (ADR 3)
    previous_close = df["close"].shift(1)
    df["log_return"] = np.log((df["close"] + df["div_cash"]) / previous_close)
    df["abs_log_return"] = df["log_return"].abs()

    daily_var = daily_variance(df)
    for window in RV_WINDOWS:
        df[f"rv_{window}d"] = realized_vol(daily_var, window)

    # value at t+5 covers t+1..t+5
    df[LABEL_COLUMN] = df[f"rv_{HORIZON}d"].shift(-HORIZON)
    return df


def build_vix_features(vix: pd.DataFrame) -> pd.DataFrame:
    df = vix.sort_values("date").reset_index(drop=True)
    df = df.rename(columns={"close": "vix"})
    df["vix_change_5d"] = df["vix"] - df["vix"].shift(VIX_CHANGE_DAYS)
    return df


def build_features(sp500: pd.DataFrame, vix: pd.DataFrame) -> pd.DataFrame:
    spy_features = build_spy_features(sp500)
    vix_features = build_vix_features(vix)

    df = spy_features.merge(vix_features, on="date", how="inner")

    df = df.dropna(subset=FEATURE_COLUMNS)

    columns = ["date"] + FEATURE_COLUMNS + [LABEL_COLUMN]
    return df[columns].reset_index(drop=True)


# one version per run, e.g. features_20261017_141703 (ADR 10)
def get_snapshot_name(built_at: datetime) -> str:
    return "features_" + built_at.strftime("%Y%m%d_%H%M%S")


def main() -> None:
    bq = BigQueryClient()

    sp500 = bq.read_table("sp500")
    vix = bq.read_table("vix")
    features = build_features(sp500, vix)

    bq.replace_all(features, "features")
    logger.info("features: %d rows", len(features))

    snapshot = get_snapshot_name(datetime.now(UTC))
    bq.create_snapshot("features", snapshot, f"commit {get_git_commit()}")
    logger.info("snapshot: %s", snapshot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
