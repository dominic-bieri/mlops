from datetime import date, datetime
from functools import lru_cache
from zoneinfo import ZoneInfo

import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel

from sp500_vol.common.baselines import FORECASTS
from sp500_vol.common.bigquery import BigQueryClient
from sp500_vol.common.config import get_git_commit
from sp500_vol.common.registry import ModelRegistry, RegisteredModel
from sp500_vol.common.schema import DRIFT_TABLE, FEATURES_TABLE, LABEL_COLUMN, PREDICTIONS_TABLE

# a weekend plus a Monday holiday, a day arrives the next morning
MAX_AGE_DAYS = 5
NEW_YORK = ZoneInfo("America/New_York")


class PredictionRow(BaseModel):
    date: date
    model: float
    rv_20d: float
    har_rv: float
    vix_scaled: float
    vix: float
    model_version: str
    predicted_at: datetime
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
    git_commit: str
    stale: bool


app = FastAPI(title="S&P 500 volatility forecast")


@lru_cache
def bq() -> BigQueryClient:
    return BigQueryClient()


def table(name: str) -> str:
    return bq().get_table_id(name)


def read_predictions() -> pd.DataFrame:
    sql = (
        f"SELECT p.*, f.{LABEL_COLUMN} AS actual FROM `{table(PREDICTIONS_TABLE)}` p "
        f"LEFT JOIN `{table(FEATURES_TABLE)}` f USING (date) ORDER BY date"
    )
    return bq().query(sql)


def read_drift() -> pd.DataFrame:
    return bq().query(f"SELECT * FROM `{table(DRIFT_TABLE)}`")


def is_backfill(predictions: pd.DataFrame) -> pd.Series:
    return predictions["backfill"].fillna(False).astype(bool)


def get_live_mae(predictions: pd.DataFrame, version: str) -> tuple[int, dict[str, float | None]]:
    live = predictions[~is_backfill(predictions)]
    known = live[(live["model_version"] == version) & live["actual"].notna()]
    mae = {}
    for name in FORECASTS:
        errors = (known[name] - known["actual"]).abs()
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
    registered = ModelRegistry().load(version)
    if registered is None:
        raise RuntimeError(f"no model {version}")
    return registered


def is_stale(newest: date, today: date) -> bool:
    return (today - newest).days > MAX_AGE_DAYS


def to_optional(value: float) -> float | None:
    return None if pd.isna(value) else float(value)


# the batch job makes the forecast, the predictions table is the log (ADR 7)
@app.get("/predictions")
def predictions() -> list[PredictionRow]:
    df = read_predictions().assign(
        actual=lambda df: df["actual"].map(to_optional), backfill=is_backfill
    )
    return [PredictionRow(**row) for row in df.to_dict("records")]


@app.get("/model")
def model() -> ModelInfo:
    predictions = read_predictions()
    newest = predictions.iloc[-1]
    version = newest["model_version"]
    registered = get_model(version)
    live_days, live_mae = get_live_mae(predictions, version)
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
        git_commit=get_git_commit(),
        stale=is_stale(newest["date"], datetime.now(NEW_YORK).date()),
    )
