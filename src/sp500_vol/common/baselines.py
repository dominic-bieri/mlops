import pandas as pd
from sklearn.linear_model import LinearRegression

from sp500_vol.features.build import LABEL_COLUMN

HAR_COLUMNS = ["rv_1d", "rv_5d", "rv_22d"]


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
