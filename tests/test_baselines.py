import pandas as pd

from sp500_vol.evaluation.baselines import TEST_START, TRAIN_END, split
from sp500_vol.features.build import HORIZON, LABEL_COLUMN


def test_no_training_label_reaches_into_test_period() -> None:
    dates = pd.bdate_range("2023-11-01", "2024-02-29").date
    features = pd.DataFrame({"date": dates, LABEL_COLUMN: 10.0})

    train, test = split(features)

    gap = features[(features["date"] > train["date"].max()) & (features["date"] <= TRAIN_END)]
    assert len(gap) == HORIZON
    assert test["date"].min() >= TEST_START
