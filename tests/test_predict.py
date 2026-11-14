from datetime import date

import numpy as np
import pytest
from fake_data import make_features
from sklearn.linear_model import LinearRegression

from sp500_vol.common.baselines import HAR_COLUMNS, get_baselines
from sp500_vol.features.build import LABEL_COLUMN
from sp500_vol.inference.predict import get_new_days, is_stale, predict
from sp500_vol.training.model import refit_model
from sp500_vol.training.train import train_and_evaluate


def test_saved_baselines_give_training_predictions() -> None:
    train = make_features(500, seed=1)
    test = make_features(50, seed=2)
    booster = refit_model(train, trees=30).booster_

    df = predict(test, booster, get_baselines(train))

    har = LinearRegression().fit(train[HAR_COLUMNS], train[LABEL_COLUMN])
    assert np.allclose(df["har_rv"], har.predict(test[HAR_COLUMNS]))


def test_metadata_has_baselines_and_train_end() -> None:
    features = make_features(2000, seed=1, start="2018-01-01")

    metadata = train_and_evaluate(features, "features_test").metadata

    assert set(metadata["har_coef"]) == set(HAR_COLUMNS)
    assert date.fromisoformat(metadata["train_end"]) < features["date"].max()
    assert set(metadata["test_mae"]) == {"model", "rv_20d", "har_rv", "vix_scaled"}


def test_first_run_predicts_only_newest_day() -> None:
    features = make_features(30, seed=1)

    new_days = get_new_days(features, set())

    assert new_days["date"].tolist() == [features["date"].max()]


def test_catches_up_missed_days() -> None:
    features = make_features(30, seed=1)
    done = set(features["date"].iloc[:27])

    new_days = get_new_days(features, done)

    assert new_days["date"].tolist() == features["date"].iloc[27:].tolist()


def test_nothing_new_twice() -> None:
    features = make_features(30, seed=1)

    assert get_new_days(features, set(features["date"])).empty


@pytest.mark.parametrize(
    ("newest", "today", "expected"),
    [
        (date(2026, 11, 13), date(2026, 11, 16), False),
        (date(2026, 11, 13), date(2026, 11, 18), False),
        (date(2026, 11, 13), date(2026, 11, 19), True),
    ],
    ids=["after weekend", "after Monday holiday", "missing day"],
)
def test_stale(newest: date, today: date, expected: bool) -> None:
    assert is_stale(newest, today) == expected
