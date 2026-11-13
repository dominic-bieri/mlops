from datetime import date

import lightgbm as lgb
import pandas as pd

from sp500_vol.features.build import FEATURE_COLUMNS, HORIZON
from sp500_vol.training.evaluate import predict_har_rv, predict_vix_scaled

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


# the first run skips the history, the model was trained on it
def get_new_days(features: pd.DataFrame, predicted: set[date]) -> pd.DataFrame:
    if not predicted:
        return features[features["date"] == features["date"].max()]
    return features[features["date"] > max(predicted)].sort_values("date")


def is_stale(newest: date, today: date) -> bool:
    return (today - newest).days > MAX_AGE_DAYS
