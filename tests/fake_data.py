import numpy as np
import pandas as pd

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
