import logging

import numpy as np
import pandas as pd

from sp500_vol.common.bigquery import BigQueryClient

logger = logging.getLogger(__name__)

TRADING_DAYS_PER_YEAR = 252
RV_WINDOWS = [5, 10, 20, 60]
HORIZON = 5
VIX_CHANGE_DAYS = 5

FEATURE_COLUMNS = [
    "log_return",
    "abs_log_return",
    "rv_5d",
    "rv_10d",
    "rv_20d",
    "rv_60d",
    "vix",
    "vix_change_5d",
]
LABEL_COLUMN = "rv_next_5d"


def realized_vol(log_returns: pd.Series, window: int) -> pd.Series:
    # percent per year, like the VIX
    squared = log_returns**2
    mean_squared = squared.rolling(window).mean()
    return np.sqrt(mean_squared * TRADING_DAYS_PER_YEAR) * 100


def build_spy_features(sp500: pd.DataFrame) -> pd.DataFrame:
    df = sp500.sort_values("date").reset_index(drop=True)

    # dividend added back, see ADR 0003
    previous_close = df["close"].shift(1)
    df["log_return"] = np.log((df["close"] + df["div_cash"]) / previous_close)
    df["abs_log_return"] = df["log_return"].abs()

    for window in RV_WINDOWS:
        df[f"rv_{window}d"] = realized_vol(df["log_return"], window)

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

    # only days with both SPY and VIX
    df = spy_features.merge(vix_features, on="date", how="inner")

    # first days have no full window
    df = df.dropna(subset=FEATURE_COLUMNS)

    columns = ["date"] + FEATURE_COLUMNS + [LABEL_COLUMN]
    return df[columns].reset_index(drop=True)


def main() -> None:
    bq = BigQueryClient()

    sp500 = bq.read_table("sp500")
    vix = bq.read_table("vix")
    features = build_features(sp500, vix)

    # full rebuild, small table
    bq.replace_all(features, "features")
    logger.info("features: %d rows", len(features))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
