import lightgbm as lgb
import numpy as np
import pandas as pd

from sp500_vol.common.baselines import predict_har_rv, predict_vix_scaled
from sp500_vol.features.build import FEATURE_COLUMNS, LABEL_COLUMN

VIX_STRESSED = 20


def get_errors(model: lgb.LGBMRegressor, baselines: dict, df: pd.DataFrame) -> pd.DataFrame:
    label = df[LABEL_COLUMN]
    return pd.DataFrame(
        {
            "model": (model.predict(df[FEATURE_COLUMNS]) - label).abs(),
            "rv_20d": (df["rv_20d"] - label).abs(),
            "har_rv": (predict_har_rv(df, baselines) - label).abs(),
            "vix_scaled": (predict_vix_scaled(df, baselines) - label).abs(),
        }
    )


def get_errors_by_year(model: lgb.LGBMRegressor, baselines: dict, df: pd.DataFrame) -> pd.DataFrame:
    errors = get_errors(model, baselines, df)
    errors["year"] = pd.to_datetime(df["date"]).dt.year
    errors["days"] = np.where(df["vix"] > VIX_STRESSED, "stressed", "calm")
    by_year = errors.groupby(["year", "days"]).mean()
    return by_year.round(2)
