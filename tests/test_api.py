from collections.abc import Iterator

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from sp500_vol.common.registry import RegisteredModel
from sp500_vol.inference import api


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    metadata = {
        "train_end": "2001-12-31",
        "test_mae": {"model": 2.5, "rv_20d": 3.0, "har_rv": 2.8, "vix_scaled": 3.1},
    }
    labels = {"run": "run-1", "snapshot": "features_1", "git_commit": "abc"}
    registered = RegisteredModel("3", labels, metadata)

    dates = pd.bdate_range("2000-01-03", periods=10).date
    predictions = pd.DataFrame(
        {
            "date": dates,
            "prediction": 15.0,
            "rv_20d": 14.0,
            "har_rv": 16.0,
            "vix_scaled": 17.0,
            "vix": 20.0,
            "horizon_days": 5,
            "model_version": "3",
            "actual": [15.5] * 5 + [np.nan] * 5,
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


def test_health_shows_model_and_commit(client: TestClient) -> None:
    body = client.get("/health").json()

    assert body["model_version"] == "3"
    assert body["git_commit"] == "def"


def test_predict_newest_day(client: TestClient) -> None:
    body = client.get("/predict").json()

    assert body["model_version"] == "3"
    assert body["horizon_days"] == 5
    assert body["prediction"] == 15.0
    assert body["features_date"] == "2000-01-14"
    # fake features are from 2000
    assert body["stale"] is True


def test_open_predictions_have_no_actual(client: TestClient) -> None:
    rows = client.get("/predictions").json()

    assert len(rows) == 10
    assert rows[0]["actual"] == 15.5
    assert rows[-1]["actual"] is None


def test_model_shows_test_and_live_mae(client: TestClient) -> None:
    body = client.get("/model").json()

    assert body["run"] == "run-1"
    assert body["test_mae"]["model"] == 2.5
    assert body["live_days"] == 5
    assert body["live_mae"]["model"] == 0.5
    assert body["live_mae"]["vix_scaled"] == 1.5
    assert body["drifted"] == ["vix"]
