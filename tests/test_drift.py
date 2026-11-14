import numpy as np
import pandas as pd
from fake_data import make_features

from sp500_vol.features.build import FEATURE_COLUMNS
from sp500_vol.inference.drift import CURRENT_DAYS, get_drift, get_threshold, psi


def test_same_distribution_has_small_psi() -> None:
    rng = np.random.default_rng(1)

    value = psi(pd.Series(rng.normal(20, 5, 5000)), pd.Series(rng.normal(20, 5, 5000)))

    assert value < 0.01


def test_empty_bins_stay_finite() -> None:
    rng = np.random.default_rng(1)
    reference = pd.Series(rng.normal(20, 5, 5000))

    value = psi(reference, pd.Series(np.full(CURRENT_DAYS, 20.0)))

    assert np.isfinite(value)


def test_known_regime_does_not_warn() -> None:
    # calm and stressed blocks of 60 days, like volatility
    rng = np.random.default_rng(1)
    levels = np.repeat(np.tile([10.0, 25.0], 20), CURRENT_DAYS)
    reference = pd.Series(levels + rng.normal(0, 1, len(levels)))
    calm = pd.Series(10 + rng.normal(0, 1, CURRENT_DAYS))

    value = psi(reference, calm)

    assert value > 0.25
    assert value < get_threshold(reference)


def test_drift_per_feature_against_training_days() -> None:
    features = make_features(500, seed=1)
    features.loc[features.index[-CURRENT_DAYS:], "vix"] += 30
    train_end = features["date"].iloc[400]

    drift = get_drift(features, train_end).set_index("feature")
    warned = drift["psi"] > drift["threshold"]

    assert list(drift.index) == FEATURE_COLUMNS
    assert warned["vix"]
    assert not warned["rv_5d"]
