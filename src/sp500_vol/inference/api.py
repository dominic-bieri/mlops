import time
from datetime import date, datetime
from functools import lru_cache
from zoneinfo import ZoneInfo

import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel

from sp500_vol.common.bigquery import BigQueryClient
from sp500_vol.common.config import get_git_commit
from sp500_vol.common.registry import RegisteredModel, load_registered_model
from sp500_vol.features.build import LABEL_COLUMN
from sp500_vol.inference.predict import is_stale

CACHE_SECONDS = 600
NEW_YORK = ZoneInfo("America/New_York")
# name in the API: column in predictions
FORECASTS = {
    "model": "prediction",
    "rv_20d": "rv_20d",
    "har_rv": "har_rv",
    "vix_scaled": "vix_scaled",
}


class Health(BaseModel):
    status: str
    model_version: str
    features_date: date
    git_commit: str


class Forecast(BaseModel):
    features_date: date
    horizon_days: int
    prediction: float
    rv_20d: float
    har_rv: float
    vix_scaled: float
    vix: float
    model_version: str
    stale: bool


class PredictionRow(BaseModel):
    date: date
    prediction: float
    rv_20d: float
    har_rv: float
    vix_scaled: float
    model_version: str
    actual: float | None
    backfill: bool


class ModelInfo(BaseModel):
    model_version: str
    run: str
    snapshot: str
    training_commit: str
    train_end: date
    test_mae: dict[str, float]
    live_days: int
    live_mae: dict[str, float | None]
    drifted: list[str]


app = FastAPI(title="S&P 500 volatility forecast")


# BigQuery at most every 10 minutes per table, the data changes once a day
cache: dict[str, tuple[float, pd.DataFrame]] = {}


@lru_cache
def bq() -> BigQueryClient:
    return BigQueryClient()


def table(name: str) -> str:
    return bq().get_table_id(name)


def read_cached(name: str, sql: str) -> pd.DataFrame:
    now = time.time()
    if name in cache:
        read_at, df = cache[name]
        if now - read_at < CACHE_SECONDS:
            return df
    df = bq().query(sql)
    cache[name] = (now, df)
    return df


def read_predictions() -> pd.DataFrame:
    sql = (
        f"SELECT p.*, f.{LABEL_COLUMN} AS actual FROM `{table('predictions')}` p "
        f"LEFT JOIN `{table('features')}` f USING (date) ORDER BY date"
    )
    return read_cached("predictions", sql)


def read_drift() -> pd.DataFrame:
    return read_cached("drift", f"SELECT * FROM `{table('drift')}`")


def is_backfill(predictions: pd.DataFrame) -> pd.Series:
    return predictions["backfill"].fillna(False).astype(bool)


def get_live_mae(predictions: pd.DataFrame, version: str) -> tuple[int, dict[str, float | None]]:
    live = predictions[~is_backfill(predictions)]
    known = live[(live["model_version"] == version) & live["actual"].notna()]
    mae = {}
    for name, column in FORECASTS.items():
        errors = (known[column] - known["actual"]).abs()
        mae[name] = to_optional(errors.mean())
    return len(known), mae


# only the newest PSI of this version counts
def get_drifted(drift: pd.DataFrame, version: str) -> list[str]:
    rows = drift[drift["model_version"] == version]
    newest = rows[rows["date"] == rows["date"].max()]
    return newest.loc[newest["psi"] > newest["threshold"], "feature"].tolist()


# a version never changes
@lru_cache
def get_model(version: str) -> RegisteredModel:
    return load_registered_model(version)


def newest() -> pd.Series:
    return read_predictions().iloc[-1]


def to_optional(value: float) -> float | None:
    return None if pd.isna(value) else float(value)


@app.get("/health")
def health() -> Health:
    row = newest()
    return Health(
        status="ok",
        model_version=row["model_version"],
        features_date=row["date"],
        git_commit=get_git_commit(),
    )


# the batch job makes the forecast, the predictions table is the log (ADR 7)
@app.get("/predict")
def predict_newest() -> Forecast:
    row = newest()
    return Forecast(
        **row.to_dict(),
        features_date=row["date"],
        stale=is_stale(row["date"], datetime.now(NEW_YORK).date()),
    )


@app.get("/predictions")
def predictions() -> list[PredictionRow]:
    # assign copies, the cached frame stays unchanged
    df = read_predictions().assign(
        actual=lambda df: df["actual"].map(to_optional), backfill=is_backfill
    )
    return [PredictionRow(**row) for row in df.to_dict("records")]


@app.get("/model")
def model() -> ModelInfo:
    version = newest()["model_version"]
    registered = get_model(version)
    live_days, live_mae = get_live_mae(read_predictions(), version)
    return ModelInfo(
        model_version=version,
        run=registered.labels.get("run", ""),
        snapshot=registered.labels.get("snapshot", ""),
        training_commit=registered.labels.get("git_commit", ""),
        train_end=registered.metadata["train_end"],
        test_mae=registered.metadata["test_mae"],
        live_days=live_days,
        live_mae=live_mae,
        drifted=get_drifted(read_drift(), version),
    )
