from datetime import date

import pandas as pd

from sp500_vol.features.build import HORIZON, LABEL_COLUMN

TEST_MONTHS = 12
VAL_MONTHS = 24


def months_before(day: date, months: int) -> date:
    timestamp = pd.Timestamp(day) - pd.DateOffset(months=months)
    return timestamp.date()


def get_cutoff(features: pd.DataFrame) -> date:
    labelled = features.dropna(subset=[LABEL_COLUMN])
    return labelled["date"].max()


def split(features: pd.DataFrame, cutoff: date) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    labelled = features.dropna(subset=[LABEL_COLUMN]).sort_values("date")
    labelled = labelled[labelled["date"] <= cutoff]

    test_start = months_before(cutoff, TEST_MONTHS)
    val_start = months_before(test_start, VAL_MONTHS)

    # gap of HORIZON rows, so no label reaches into the next window
    train = labelled[labelled["date"] <= val_start].iloc[:-HORIZON]
    in_val = (labelled["date"] > val_start) & (labelled["date"] <= test_start)
    val = labelled[in_val].iloc[:-HORIZON]
    test = labelled[labelled["date"] > test_start]
    return train, val, test
