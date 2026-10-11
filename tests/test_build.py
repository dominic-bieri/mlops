import numpy as np
import pandas as pd
import pytest

from sp500_vol.features.build import (
    FEATURE_COLUMNS,
    LABEL_COLUMN,
    RV_WINDOWS,
    build_features,
    build_spy_features,
)

DAYS = 100


def make_sp500() -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-02", periods=DAYS).date
    rng = np.random.default_rng(42)
    returns = rng.normal(0, 0.01, DAYS)
    close = 400 * np.exp(np.cumsum(returns))
    return pd.DataFrame({"date": dates, "close": close, "div_cash": 0.0})


def make_vix() -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-02", periods=DAYS).date
    close = np.linspace(12, 20, DAYS)
    return pd.DataFrame({"date": dates, "close": close})


def test_features_do_not_look_into_the_future() -> None:
    sp500 = make_sp500()
    vix = make_vix()
    cut = 80

    changed_sp500 = sp500.copy()
    changed_sp500.loc[cut + 1 :, "close"] = changed_sp500.loc[cut + 1 :, "close"] * 1.5
    changed_vix = vix.copy()
    changed_vix.loc[cut + 1 :, "close"] = 80.0

    before = build_features(sp500, vix)
    after = build_features(changed_sp500, changed_vix)

    cut_date = sp500.loc[cut, "date"]
    before_row = before[before["date"] == cut_date]
    after_row = after[after["date"] == cut_date]

    assert before_row[FEATURE_COLUMNS].equals(after_row[FEATURE_COLUMNS])
    assert before_row[LABEL_COLUMN].iloc[0] != after_row[LABEL_COLUMN].iloc[0]


def test_label_is_realized_vol_of_next_five_days() -> None:
    df = build_spy_features(make_sp500())

    assert df.loc[50, LABEL_COLUMN] == pytest.approx(df.loc[55, "rv_5d"])


def test_last_five_days_have_no_label() -> None:
    df = build_features(make_sp500(), make_vix())

    labels = df[LABEL_COLUMN]
    assert labels.tail(5).isna().all()
    assert labels.iloc[:-5].notna().all()


def test_first_days_without_full_window_are_dropped() -> None:
    sp500 = make_sp500()

    df = build_features(sp500, make_vix())

    # 1 day for the first return, then the longest window
    assert df["date"].iloc[0] == sp500.loc[max(RV_WINDOWS), "date"]


def test_dividend_drop_is_not_a_return() -> None:
    sp500 = pd.DataFrame(
        {
            "date": pd.bdate_range("2024-03-14", periods=2).date,
            "close": [510.0, 508.5],
            "div_cash": [0.0, 1.5],
        }
    )

    df = build_spy_features(sp500)

    assert df.loc[1, "log_return"] == pytest.approx(0.0)
