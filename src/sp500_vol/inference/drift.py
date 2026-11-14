from datetime import date

import numpy as np
import pandas as pd

from sp500_vol.features.build import FEATURE_COLUMNS

BINS = 10
CURRENT_DAYS = 60
# a warning when the last 60 days are rarer than 95 % of the 60-day windows in training
THRESHOLD_QUANTILE = 0.95
# every 20th window is enough for the threshold
WINDOW_STEP = 20


def psi(reference: pd.Series, current: pd.Series, bins: int = BINS) -> float:
    edges = np.unique(np.quantile(reference, np.linspace(0, 1, bins + 1)))
    edges[0], edges[-1] = -np.inf, np.inf

    expected_counts = np.histogram(reference, edges)[0]
    actual_counts = np.histogram(current, edges)[0]
    # half a count per bin, an empty bin would give log(0)
    expected = (expected_counts + 0.5) / (len(reference) + 0.5 * len(expected_counts))
    actual = (actual_counts + 0.5) / (len(current) + 0.5 * len(actual_counts))
    return float(np.sum((actual - expected) * np.log(actual / expected)))


# volatility comes in regimes, any 60 days differ from 30 years, a fixed 0.25 always warns
def get_threshold(reference: pd.Series) -> float:
    values = []
    for start in range(0, len(reference) - CURRENT_DAYS + 1, WINDOW_STEP):
        window = reference.iloc[start : start + CURRENT_DAYS]
        values.append(psi(reference, window))
    return float(np.quantile(values, THRESHOLD_QUANTILE))


def get_drift(features: pd.DataFrame, train_end: date) -> pd.DataFrame:
    df = features.sort_values("date")
    reference = df[df["date"] <= train_end]
    current = df.tail(CURRENT_DAYS)

    rows = []
    for column in FEATURE_COLUMNS:
        value = psi(reference[column], current[column])
        threshold = get_threshold(reference[column])
        rows.append({"feature": column, "psi": value, "threshold": threshold})
    return pd.DataFrame(rows)
