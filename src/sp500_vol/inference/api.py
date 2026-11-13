import time
from collections.abc import Callable
from datetime import date, datetime
from functools import lru_cache
from zoneinfo import ZoneInfo

import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel

from sp500_vol.common.bigquery import BigQueryClient
from sp500_vol.common.config import get_git_commit
from sp500_vol.features.build import LABEL_COLUMN
from sp500_vol.inference.drift import PSI_WARNING
from sp500_vol.inference.model import RegisteredModel, load_registered_model
from sp500_vol.inference.predict import is_stale

CACHE_SECONDS = 600
NEW_YORK = ZoneInfo("America/New_York")
FORECASTS = ["model", "rv_20d", "har_rv", "vix_scaled"]


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


def cached(read: Callable[..., pd.DataFrame]) -> Callable[..., pd.DataFrame]:
    @lru_cache(maxsize=8)
    def read_period(period: int, *args: str) -> pd.DataFrame:
        return read(*args)

    return lambda *args: read_period(int(time.time() // CACHE_SECONDS), *args)


@lru_cache
def bq() -> BigQueryClient:
    return BigQueryClient()


def table(name: str) -> str:
    return bq().get_table_id(name)


@cached
def read_predictions() -> pd.DataFrame:
    sql = (
        f"SELECT p.*, f.{LABEL_COLUMN} AS actual FROM `{table('predictions')}` p "
        f"LEFT JOIN `{table('features')}` f USING (date) ORDER BY date"
    )
    return bq().query(sql)


@cached
def read_live_errors(version: str) -> pd.DataFrame:
    averages = ", ".join(f"AVG({name}_error) AS {name}" for name in FORECASTS)
    sql = (
        f"SELECT COUNT(*) AS days, {averages} FROM `{table('prediction_errors')}` "
        f"WHERE model_version = '{version}'"
    )
    return bq().query(sql)


@cached
def read_drifted(version: str) -> pd.DataFrame:
    sql = (
        f"SELECT feature FROM `{table('drift')}` WHERE model_version = '{version}' "
        f"AND psi > {PSI_WARNING} AND date = "
        f"(SELECT MAX(date) FROM `{table('drift')}` WHERE model_version = '{version}')"
    )
    return bq().query(sql)


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
    df = read_predictions().assign(actual=lambda df: df["actual"].map(to_optional))
    return [PredictionRow(**row) for row in df.to_dict("records")]


@app.get("/model")
def model() -> ModelInfo:
    version = newest()["model_version"]
    registered = get_model(version)
    live = read_live_errors(version).iloc[0]
    return ModelInfo(
        model_version=version,
        run=registered.labels.get("run", ""),
        snapshot=registered.labels.get("snapshot", ""),
        training_commit=registered.labels.get("git_commit", ""),
        train_end=registered.metadata["train_end"],
        test_mae=registered.metadata["test_mae"],
        live_days=int(live["days"]),
        live_mae={name: to_optional(live[name]) for name in FORECASTS},
        drifted=read_drifted(version)["feature"].tolist(),
    )
