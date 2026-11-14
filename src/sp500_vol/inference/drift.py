from datetime import date

import numpy as np
import pandas as pd

from sp500_vol.features.build import FEATURE_COLUMNS

BINS = 10
CURRENT_DAYS = 60
PSI_WARNING = 0.25
# avoids log(0) for empty bins
MIN_SHARE = 1e-4


def psi(reference: pd.Series, current: pd.Series, bins: int = BINS) -> float:
    edges = np.unique(np.quantile(reference, np.linspace(0, 1, bins + 1)))
    edges[0], edges[-1] = -np.inf, np.inf

    expected = np.histogram(reference, edges)[0] / len(reference)
    actual = np.histogram(current, edges)[0] / len(current)
    expected = np.clip(expected, MIN_SHARE, None)
    actual = np.clip(actual, MIN_SHARE, None)
    return float(np.sum((actual - expected) * np.log(actual / expected)))


def get_drift(features: pd.DataFrame, train_end: date) -> pd.DataFrame:
    df = features.sort_values("date")
    reference = df[df["date"] <= train_end]
    current = df.tail(CURRENT_DAYS)
    values = [psi(reference[column], current[column]) for column in FEATURE_COLUMNS]
    return pd.DataFrame({"feature": FEATURE_COLUMNS, "psi": values})
