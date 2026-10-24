from datetime import date

import pandas as pd

from sp500_vol.features.build import HORIZON, LABEL_COLUMN
from sp500_vol.training.split import get_cutoff, split


def make_features(start: str, end: str) -> pd.DataFrame:
    dates = pd.bdate_range(start, end).date
    return pd.DataFrame({"date": dates, LABEL_COLUMN: 10.0})


def count_between(features: pd.DataFrame, after: date, before: date) -> int:
    rows = features[(features["date"] > after) & (features["date"] < before)]
    return len(rows)


def test_windows_end_at_cutoff() -> None:
    features = make_features("2015-01-01", "2026-10-16")

    train, val, test = split(features, date(2026, 10, 16))

    assert test["date"].max() == date(2026, 10, 16)
    assert test["date"].min() > date(2025, 10, 16)
    assert val["date"].min() > date(2023, 10, 16)
    assert train["date"].max() < date(2023, 10, 16)


def test_gap_between_windows() -> None:
    features = make_features("2015-01-01", "2026-10-16")

    train, val, test = split(features, date(2026, 10, 16))

    assert count_between(features, train["date"].max(), val["date"].min()) == HORIZON
    assert count_between(features, val["date"].max(), test["date"].min()) == HORIZON


def test_windows_move_with_new_data() -> None:
    features = make_features("2015-01-01", "2026-10-16")

    train_old, _, test_old = split(features, date(2026, 9, 16))
    train_new, _, test_new = split(features, date(2026, 10, 16))

    assert len(train_new) > len(train_old)
    assert abs(len(test_new) - len(test_old)) <= 2


def test_cutoff_is_newest_label() -> None:
    features = make_features("2026-01-01", "2026-01-31")
    features.loc[features.index[-HORIZON:], LABEL_COLUMN] = None

    cutoff = get_cutoff(features)

    assert cutoff == features["date"].iloc[-HORIZON - 1]
