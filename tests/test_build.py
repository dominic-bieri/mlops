import pandas as pd
import pytest
from fake_data import make_data

from sp500_vol.features.build import (
    FEATURE_COLUMNS,
    HORIZON,
    LABEL_COLUMN,
    RV_WINDOWS,
    build_features,
    build_spy_features,
    daily_variance,
)


def test_features_do_not_look_into_the_future() -> None:
    sp500, vix = make_data()
    cut = 80

    changed_sp500 = sp500.copy()
    prices = ["open", "high", "low", "close"]
    changed_sp500.loc[cut + 1 :, prices] = changed_sp500.loc[cut + 1 :, prices] * 1.5
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
    sp500, _ = make_data()

    df = build_spy_features(sp500)

    assert df.loc[50, LABEL_COLUMN] == pytest.approx(df.loc[55, "rv_5d"])


def test_last_five_days_have_no_label() -> None:
    df = build_features(*make_data())

    labels = df[LABEL_COLUMN]
    assert labels.tail(HORIZON).isna().all()
    assert labels.iloc[:-HORIZON].notna().all()


def test_first_days_without_full_window_are_dropped() -> None:
    sp500, vix = make_data()

    df = build_features(sp500, vix)

    assert df["date"].iloc[0] == sp500.loc[max(RV_WINDOWS), "date"]


def test_dividend_drop_is_not_a_return() -> None:
    sp500 = pd.DataFrame(
        {
            "date": pd.bdate_range("2024-03-14", periods=2).date,
            "open": [510.0, 508.5],
            "high": [510.0, 508.5],
            "low": [510.0, 508.5],
            "close": [510.0, 508.5],
            "div_cash": [0.0, 1.5],
        }
    )

    df = build_spy_features(sp500)

    assert df.loc[1, "log_return"] == pytest.approx(0.0)
    assert daily_variance(sp500).iloc[1] == pytest.approx(0.0)


def test_without_intraday_move_variance_is_squared_return() -> None:
    sp500, _ = make_data()
    for column in ["open", "high", "low"]:
        sp500[column] = sp500["close"]

    df = build_spy_features(sp500)

    assert daily_variance(sp500).iloc[1:].to_numpy() == pytest.approx(
        (df["log_return"] ** 2).iloc[1:].to_numpy()
    )
