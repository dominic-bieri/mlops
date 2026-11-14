from datetime import date

import lightgbm as lgb
import pandas as pd

from sp500_vol.common.baselines import predict_har_rv, predict_vix_scaled
from sp500_vol.features.build import FEATURE_COLUMNS, HORIZON

# a weekend plus a Monday holiday, a day arrives the next morning
MAX_AGE_DAYS = 5


def predict(features: pd.DataFrame, booster: lgb.Booster, metadata: dict) -> pd.DataFrame:
    df = pd.DataFrame(
        {
            "date": features["date"],
            "horizon_days": HORIZON,
            "prediction": booster.predict(features[FEATURE_COLUMNS]),
            "rv_20d": features["rv_20d"],
            "har_rv": predict_har_rv(features, metadata),
            "vix_scaled": predict_vix_scaled(features, metadata),
            "vix": features["vix"],
        }
    )
    return df.reset_index(drop=True)


def get_new_days(features: pd.DataFrame, predicted: set[date], train_end: date) -> pd.DataFrame:
    unseen = features[features["date"] > train_end]
    missing = [day not in predicted for day in unseen["date"]]
    return unseen[missing].sort_values("date")


def get_backfill(days: pd.Series, predicted: set[date]) -> pd.Series:
    first_live = min(predicted) if predicted else days.max()
    return days < first_live


def is_stale(newest: date, today: date) -> bool:
    return (today - newest).days > MAX_AGE_DAYS
