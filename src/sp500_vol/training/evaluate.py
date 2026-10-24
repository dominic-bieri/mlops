import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from sp500_vol.features.build import FEATURE_COLUMNS, LABEL_COLUMN

HAR_COLUMNS = ["rv_1d", "rv_5d", "rv_22d"]
VIX_STRESSED = 20


def fit_har(train: pd.DataFrame) -> LinearRegression:
    return LinearRegression().fit(train[HAR_COLUMNS], train[LABEL_COLUMN])


# removes the risk premium (ADR 4)
def get_vix_factor(train: pd.DataFrame) -> float:
    return train[LABEL_COLUMN].mean() / train["vix"].mean()


def get_errors(model: lgb.LGBMRegressor, train: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
    har = fit_har(train)
    vix_factor = get_vix_factor(train)
    label = df[LABEL_COLUMN]
    return pd.DataFrame(
        {
            "model": (model.predict(df[FEATURE_COLUMNS]) - label).abs(),
            "rv_20d": (df["rv_20d"] - label).abs(),
            "har_rv": (har.predict(df[HAR_COLUMNS]) - label).abs(),
            "vix_scaled": (vix_factor * df["vix"] - label).abs(),
        }
    )


def get_errors_by_year(
    model: lgb.LGBMRegressor, train: pd.DataFrame, df: pd.DataFrame
) -> pd.DataFrame:
    errors = get_errors(model, train, df)
    errors["year"] = pd.to_datetime(df["date"]).dt.year
    errors["days"] = np.where(df["vix"] > VIX_STRESSED, "stressed", "calm")
    by_year = errors.groupby(["year", "days"]).mean()
    return by_year.round(2)
