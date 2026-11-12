from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import lightgbm as lgb
import pytest
from fake_data import make_features
from sklearn.metrics import mean_absolute_error

from sp500_vol.features.build import FEATURE_COLUMNS, LABEL_COLUMN
from sp500_vol.training.model import refit_model
from sp500_vol.training.train import (
    MAX_MODEL_AGE,
    get_current_mae,
    get_windows,
    should_register,
)


@pytest.mark.parametrize(
    ("test_mae", "har_mae", "current_mae", "expected"),
    [
        (2.88, 3.28, None, True),
        (3.30, 3.28, None, False),
        (2.86, 3.25, 2.86, True),
        (2.87, 3.25, 2.86, False),
        (3.30, 3.25, 3.50, False),
    ],
    ids=[
        "no current, beats HAR",
        "no current, loses to HAR",
        "tie with current",
        "worse than current",
        "beats current, loses to HAR",
    ],
)
def test_should_register(
    test_mae: float, har_mae: float, current_mae: float | None, expected: bool
) -> None:
    assert should_register(test_mae, har_mae, current_mae) == expected


def make_current(booster: lgb.Booster, age: timedelta) -> tuple[SimpleNamespace, SimpleNamespace]:
    current = SimpleNamespace(version_create_time=datetime.now(UTC) - age)
    registry = SimpleNamespace(load_model=lambda registered: booster)
    return registry, current


def test_current_mae_on_new_test() -> None:
    model = refit_model(make_features(500, seed=1), trees=30)
    test = make_features(200, seed=2)
    registry, current = make_current(model.booster_, timedelta(days=30))

    current_mae = get_current_mae(registry, current, test)

    expected = mean_absolute_error(test[LABEL_COLUMN], model.predict(test[FEATURE_COLUMNS]))
    assert current_mae == pytest.approx(expected)


def test_no_current_model() -> None:
    assert get_current_mae(SimpleNamespace(), None, make_features(10, seed=1)) is None


def test_old_current_model_does_not_count() -> None:
    model = refit_model(make_features(500, seed=1), trees=30)
    registry, current = make_current(model.booster_, MAX_MODEL_AGE + timedelta(days=1))

    assert get_current_mae(registry, current, make_features(200, seed=2)) is None


def test_current_model_with_other_features_does_not_count() -> None:
    train = make_features(500, seed=1)
    other = [f"old_{column}" for column in FEATURE_COLUMNS]
    renamed = train[FEATURE_COLUMNS].set_axis(other, axis=1)
    model = lgb.LGBMRegressor(n_estimators=10, verbose=-1).fit(renamed, train[LABEL_COLUMN])
    registry, current = make_current(model.booster_, timedelta(days=30))

    assert get_current_mae(registry, current, make_features(200, seed=2)) is None


def test_windows_name_dates_and_rows() -> None:
    features = make_features(30, seed=1, start="2026-01-01")

    windows = get_windows(features[:10], features[10:20], features[20:])

    assert windows["train_start"] == "2026-01-01"
    assert windows["test_end"] == str(features["date"].iloc[-1])
    assert windows["val_rows"] == 10
