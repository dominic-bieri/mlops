import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from sp500_vol.features.build import FEATURE_COLUMNS, LABEL_COLUMN

HAR_COLUMNS = ["rv_1d", "rv_5d", "rv_22d"]
VIX_STRESSED = 20


# the VIX factor removes the risk premium (ADR 4)
def get_baselines(train: pd.DataFrame) -> dict:
    har = LinearRegression().fit(train[HAR_COLUMNS], train[LABEL_COLUMN])
    return {
        "har_intercept": float(har.intercept_),
        "har_coef": dict(zip(HAR_COLUMNS, har.coef_.tolist(), strict=True)),
        "vix_factor": float(train[LABEL_COLUMN].mean() / train["vix"].mean()),
    }


def predict_har_rv(df: pd.DataFrame, baselines: dict) -> pd.Series:
    terms = [coef * df[column] for column, coef in baselines["har_coef"].items()]
    return baselines["har_intercept"] + sum(terms)


def predict_vix_scaled(df: pd.DataFrame, baselines: dict) -> pd.Series:
    return baselines["vix_factor"] * df["vix"]


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
