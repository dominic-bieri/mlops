from datetime import date

import numpy as np
import pandas as pd
import pytest

from sp500_vol.features.build import FEATURE_COLUMNS, HORIZON, LABEL_COLUMN, build_features
from sp500_vol.features.ingest import only_new

DAYS = 80
BACKFILL_DAYS = 65


def make_data(shock_day: int | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    dates = pd.bdate_range("2024-01-02", periods=DAYS).date
    rng = np.random.default_rng(7)
    returns = rng.normal(0, 0.01, DAYS)
    if shock_day is not None:
        returns[shock_day] = -0.10
    close = 400 * np.exp(np.cumsum(returns))
    sp500 = pd.DataFrame(
        {
            "date": dates,
            "open": close,
            "high": close * 1.005,
            "low": close * 0.995,
            "close": close,
            "div_cash": 0.0,
        }
    )
    vix = pd.DataFrame({"date": dates, "close": np.linspace(12, 20, DAYS)})
    return sp500, vix


def next_morning(day: date) -> pd.Timestamp:
    return pd.Timestamp(day, tz="UTC") + pd.Timedelta(days=1, hours=13)


def replay(
    sp500: pd.DataFrame, vix: pd.DataFrame, late_vix_day: date | None = None
) -> tuple[dict[date, pd.DataFrame], pd.DataFrame]:
    dates = sp500["date"].tolist()
    backfill_day = dates[BACKFILL_DAYS - 1]
    stored_sp500 = only_new(sp500[sp500["date"] <= backfill_day], set(), next_morning(backfill_day))
    stored_vix = only_new(vix[vix["date"] <= backfill_day], set(), next_morning(backfill_day))

    snapshots = {}
    for day in dates[BACKFILL_DAYS:]:
        loaded_at = next_morning(day)
        known_vix = vix[vix["date"] < day] if day == late_vix_day else vix[vix["date"] <= day]

        new_sp500 = only_new(sp500[sp500["date"] <= day], set(stored_sp500["date"]), loaded_at)
        new_vix = only_new(known_vix, set(stored_vix["date"]), loaded_at)
        stored_sp500 = pd.concat([stored_sp500, new_sp500])
        stored_vix = pd.concat([stored_vix, new_vix])

        snapshots[day] = build_features(stored_sp500, stored_vix)
    return snapshots, stored_vix


def test_normal_days_keep_features_and_get_label_after_five_days() -> None:
    sp500, vix = make_data()
    final = build_features(sp500, vix).set_index("date")

    snapshots, _ = replay(sp500, vix)

    for features in snapshots.values():
        features = features.set_index("date")
        known = final.loc[features.index]
        labels = features[LABEL_COLUMN]

        assert features[FEATURE_COLUMNS].to_numpy() == pytest.approx(
            known[FEATURE_COLUMNS].to_numpy()
        )
        assert labels.tail(HORIZON).isna().all()
        assert labels.iloc[:-HORIZON].to_numpy() == pytest.approx(
            known[LABEL_COLUMN].iloc[:-HORIZON].to_numpy()
        )


def test_market_shock_is_unknown_the_day_before() -> None:
    shock = 70
    sp500, vix = make_data(shock_day=shock)
    calm_sp500, _ = make_data()
    day_before = sp500["date"][shock - 1]
    shock_day = sp500["date"][shock]

    shocked, _ = replay(sp500, vix)
    calm, _ = replay(calm_sp500, vix)

    assert shocked[day_before].equals(calm[day_before])
    assert shocked[shock_day]["rv_1d"].iloc[-1] > 3 * calm[shock_day]["rv_1d"].iloc[-1]


def test_late_vix_day_appears_one_run_later() -> None:
    sp500, vix = make_data()
    late_day = sp500["date"][70]
    next_day = sp500["date"][71]

    snapshots, stored_vix = replay(sp500, vix, late_vix_day=late_day)

    assert late_day not in snapshots[late_day]["date"].tolist()
    assert late_day in snapshots[next_day]["date"].tolist()
    assert stored_vix.set_index("date").loc[late_day, "loaded_at"] == next_morning(next_day)
