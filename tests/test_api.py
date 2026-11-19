from collections.abc import Iterator
from datetime import UTC, date, datetime

import numpy as np
import pandas as pd
import pytest
from fake_data import make_features
from fastapi.testclient import TestClient

from sp500_vol.common.registry import RegisteredModel
from sp500_vol.inference import api
from sp500_vol.training.model import refit_model


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    metadata = {
        "train_end": "2001-12-31",
        "test_mae": {"model": 2.5, "rv_20d": 3.0, "har_rv": 2.8, "vix_scaled": 3.1},
    }
    labels = {"run": "run-1", "snapshot": "features_1", "git_commit": "abc"}
    booster = refit_model(make_features(50, seed=1), trees=1).booster_
    created = datetime(2002, 1, 1, tzinfo=UTC)
    registered = RegisteredModel("3", labels, created, metadata, booster)

    dates = pd.bdate_range("2000-01-03", periods=10).date
    predictions = pd.DataFrame(
        {
            "date": dates,
            "model": 15.0,
            "rv_20d": 14.0,
            "har_rv": 16.0,
            "vix_scaled": 17.0,
            "vix": 20.0,
            "horizon_days": 5,
            "model_version": "3",
            "predicted_at": pd.Timestamp("2000-01-15 15:00", tz="UTC"),
            "actual": [15.5] * 5 + [np.nan] * 5,
            "backfill": [None, True] + [False] * 8,
        }
    )
    # rv_5d drifted earlier, only vix in the newest run
    drift = pd.DataFrame(
        {
            "date": [dates[-2], dates[-1], dates[-1]],
            "feature": ["rv_5d", "rv_5d", "vix"],
            "psi": [0.4, 0.1, 0.3],
            "threshold": 0.2,
            "model_version": "3",
        }
    )

    monkeypatch.setattr(api, "get_model", lambda version: registered)
    monkeypatch.setattr(api, "read_predictions", lambda: predictions)
    monkeypatch.setattr(api, "read_drift", lambda: drift)
    monkeypatch.setenv("GITHUB_SHA", "def")
    with TestClient(api.app) as test_client:
        yield test_client


def test_open_predictions_have_no_actual(client: TestClient) -> None:
    rows = client.get("/predictions").json()

    assert len(rows) == 10
    assert rows[0]["actual"] == 15.5
    assert rows[0]["backfill"] is False
    assert rows[1]["backfill"] is True
    assert rows[-1]["actual"] is None
    assert rows[-1]["vix"] == 20.0
    assert rows[-1]["predicted_at"] == "2000-01-15T15:00:00Z"


def test_model_shows_test_and_live_mae(client: TestClient) -> None:
    body = client.get("/model").json()

    assert body["run"] == "run-1"
    assert body["test_mae"]["model"] == 2.5
    assert body["live_days"] == 4
    assert body["live_mae"]["model"] == 0.5
    assert body["live_mae"]["vix_scaled"] == 1.5
    assert body["drifted"] == ["vix"]
    assert body["git_commit"] == "def"
    # fake features are from 2000
    assert body["stale"] is True


@pytest.mark.parametrize(
    ("newest", "today", "expected"),
    [
        (date(2026, 11, 13), date(2026, 11, 16), False),
        (date(2026, 11, 13), date(2026, 11, 18), False),
        (date(2026, 11, 13), date(2026, 11, 19), True),
    ],
    ids=["after weekend", "after Monday holiday", "missing day"],
)
def test_stale(newest: date, today: date, expected: bool) -> None:
    assert api.is_stale(newest, today) == expected
