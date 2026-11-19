from datetime import date

import pandas as pd

# a weekend plus a Monday holiday, a day arrives the next morning
MAX_AGE_DAYS = 5


def get_new_days(features: pd.DataFrame, predicted: set[date], train_end: date) -> pd.DataFrame:
    unseen = features[features["date"] > train_end]
    missing = [day not in predicted for day in unseen["date"]]
    return unseen[missing].sort_values("date")


def get_backfill(days: pd.Series, predicted: set[date]) -> pd.Series:
    first_live = min(predicted) if predicted else days.max()
    return days < first_live


def is_stale(newest: date, today: date) -> bool:
    return (today - newest).days > MAX_AGE_DAYS
