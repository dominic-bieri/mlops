from datetime import UTC, datetime

import numpy as np
import pandas as pd

from sp500_vol.common.baselines import get_baselines
from sp500_vol.common.registry import RegisteredModel
from sp500_vol.common.schema import FEATURE_COLUMNS, LABEL_COLUMN
from sp500_vol.training.model import refit_model

DAYS = 100


def make_data(shock_day: int | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    dates = pd.bdate_range("2024-01-02", periods=DAYS).date
    rng = np.random.default_rng(42)
    returns = rng.normal(0, 0.01, DAYS)
    if shock_day is not None:
        returns[shock_day] = -0.10
    close = 400 * np.exp(np.cumsum(returns))
    open_ = close * np.exp(rng.normal(0, 0.003, DAYS))
    sp500 = pd.DataFrame(
        {
            "date": dates,
            "open": open_,
            "high": np.maximum(open_, close) * 1.004,
            "low": np.minimum(open_, close) * 0.996,
            "close": close,
            "div_cash": 0.0,
        }
    )
    vix = pd.DataFrame({"date": dates, "close": np.linspace(12, 20, DAYS)})
    return sp500, vix


def make_features(rows: int, seed: int, start: str = "2000-01-03") -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({"date": pd.bdate_range(start, periods=rows).date})
    for column in FEATURE_COLUMNS:
        df[column] = rng.uniform(5, 40, rows)

    noise = rng.normal(0, 1, rows)
    df[LABEL_COLUMN] = 0.9 * df["rv_5d"] + noise
    return df


class FakeRegistry:
    def __init__(self, features: pd.DataFrame) -> None:
        train_days = features.iloc[:400]
        booster = refit_model(train_days, trees=30).booster_
        metadata = {"train_end": str(train_days["date"].max()), **get_baselines(train_days)}
        created = datetime.now(UTC)
        self.champion = RegisteredModel("3", {"run": "run-1"}, created, metadata, booster)

    def load(self, version: str) -> RegisteredModel | None:
        return self.champion
