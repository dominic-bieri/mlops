import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error

from sp500_vol.features.build import FEATURE_COLUMNS, LABEL_COLUMN
from sp500_vol.training.model import fit_model, refit_model


def make_features(rows: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    df = pd.DataFrame()
    for column in FEATURE_COLUMNS:
        df[column] = rng.uniform(5, 40, rows)

    noise = rng.normal(0, 1, rows)
    df[LABEL_COLUMN] = 0.9 * df["rv_5d"] + noise
    return df


def test_same_result_on_every_run() -> None:
    train = make_features(500, seed=1)
    val = make_features(200, seed=2)

    first = fit_model(train, val)
    second = fit_model(train, val)

    first_prediction = first.predict(val[FEATURE_COLUMNS])
    second_prediction = second.predict(val[FEATURE_COLUMNS])
    assert np.array_equal(first_prediction, second_prediction)


def test_model_beats_mean() -> None:
    train = make_features(500, seed=1)
    val = make_features(200, seed=2)
    test = make_features(200, seed=3)

    model = fit_model(train, val)

    prediction = model.predict(test[FEATURE_COLUMNS])
    mean = np.full(len(test), train[LABEL_COLUMN].mean())
    model_mae = mean_absolute_error(test[LABEL_COLUMN], prediction)
    mean_mae = mean_absolute_error(test[LABEL_COLUMN], mean)
    assert model_mae < mean_mae


def test_refit_uses_given_trees() -> None:
    labelled = make_features(500, seed=1)

    model = refit_model(labelled, trees=30)

    assert model.booster_.num_trees() == 30


def test_saved_model_keeps_feature_names() -> None:
    model = refit_model(make_features(500, seed=1), trees=30)

    booster = lgb.Booster(model_str=model.booster_.model_to_string())

    assert booster.feature_name() == FEATURE_COLUMNS
