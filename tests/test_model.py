import lightgbm as lgb
import numpy as np
from fake_data import make_features
from sklearn.metrics import mean_absolute_error

from sp500_vol.features.build import FEATURE_COLUMNS, LABEL_COLUMN
from sp500_vol.training.model import fit_model, refit_model
from sp500_vol.training.train import train_and_evaluate


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


def test_train_and_evaluate_beats_20_day_baseline() -> None:
    features = make_features(2000, seed=1, start="2018-01-01")

    result = train_and_evaluate(features, "features_test")

    assert result.model.booster_.num_trees() == result.params["trees"]
    assert result.metrics["test_mae"] < result.metrics["rv_20d_test_mae"]
