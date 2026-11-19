from datetime import date

import pandas as pd
import pytest
from fake_data import FakeRegistry, make_features

from sp500_vol.inference import batch
from sp500_vol.training import train


class FakeBigQuery:
    def __init__(self, features: pd.DataFrame) -> None:
        self.features = features
        self.written_tables = []

    def get_latest_snapshot(self, prefix: str) -> str:
        return "features_test"

    def read_table(self, table: str) -> pd.DataFrame:
        return self.features

    def get_dates(self, table: str) -> set[date]:
        return set()

    def append(self, df: pd.DataFrame, table: str) -> None:
        self.written_tables.append(table)


def test_local_training_tracks_and_registers_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    bq = FakeBigQuery(make_features(2000, seed=1, start="2018-01-01"))
    tracked = []
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.setattr(train, "BigQueryClient", lambda: bq)
    monkeypatch.setattr(train, "track_and_register", tracked.append)

    train.main()

    assert tracked == []


def test_local_inference_writes_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    features = make_features(500, seed=1)
    bq = FakeBigQuery(features)
    registry = FakeRegistry(features)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.setattr(batch, "BigQueryClient", lambda: bq)
    monkeypatch.setattr(batch, "ModelRegistry", lambda: registry)

    batch.main()

    assert bq.written_tables == []


def test_inference_in_github_actions_writes_predictions_and_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    features = make_features(500, seed=1)
    bq = FakeBigQuery(features)
    registry = FakeRegistry(features)
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setattr(batch, "BigQueryClient", lambda: bq)
    monkeypatch.setattr(batch, "ModelRegistry", lambda: registry)

    batch.main()

    assert bq.written_tables == ["predictions", "drift"]
