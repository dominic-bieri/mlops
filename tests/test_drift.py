import numpy as np
import pandas as pd
from fake_data import make_features

from sp500_vol.features.build import FEATURE_COLUMNS
from sp500_vol.inference.drift import CURRENT_DAYS, PSI_WARNING, get_drift, psi


def test_same_distribution_has_small_psi() -> None:
    rng = np.random.default_rng(1)

    value = psi(pd.Series(rng.normal(20, 5, 5000)), pd.Series(rng.normal(20, 5, 5000)))

    assert value < 0.01


def test_shifted_distribution_warns() -> None:
    rng = np.random.default_rng(1)

    value = psi(pd.Series(rng.normal(20, 5, 5000)), pd.Series(rng.normal(30, 5, CURRENT_DAYS)))

    assert value > PSI_WARNING


def test_drift_per_feature_against_training_days() -> None:
    features = make_features(500, seed=1)
    features.loc[features.index[-CURRENT_DAYS:], "vix"] += 30
    train_end = features["date"].iloc[400]

    drift = get_drift(features, train_end).set_index("feature")["psi"]

    assert list(drift.index) == FEATURE_COLUMNS
    assert drift["vix"] > PSI_WARNING
    assert drift["rv_5d"] < PSI_WARNING
