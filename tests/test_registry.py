import json
from datetime import UTC, datetime
from types import SimpleNamespace

import lightgbm as lgb
import pytest
from fake_data import make_features
from google.api_core.exceptions import NotFound

from sp500_vol.common import registry
from sp500_vol.common.registry import CHAMPION, ModelRegistry
from sp500_vol.common.schema import FEATURE_COLUMNS, LABEL_COLUMN

CREATED = datetime(2026, 11, 1, tzinfo=UTC)


def fake_registry(
    monkeypatch: pytest.MonkeyPatch, files: dict[str, str], alias: bool = True
) -> ModelRegistry:
    class FakeModel:
        resource_name = "models/1"
        version_id = "3"
        labels = {"run": "run-1"}
        version_create_time = CREATED
        uri = "gs://bucket/run-1"

        def __init__(self, name: str) -> None:
            if not alias:
                raise NotFound(name)

        @staticmethod
        def list(filter: str) -> list:
            return [FakeModel] if files else []

    def from_uri(uri: str, client: object) -> SimpleNamespace:
        file = uri.removeprefix(f"{FakeModel.uri}/")
        if file not in files:
            raise NotFound(uri)
        return SimpleNamespace(download_as_text=lambda: files[file])

    monkeypatch.setenv("GCP_PROJECT_ID", "project")
    monkeypatch.setenv("GCP_REGION", "region")
    monkeypatch.setattr(registry.aiplatform, "init", lambda **kwargs: None)
    monkeypatch.setattr(registry.aiplatform, "Model", FakeModel)
    monkeypatch.setattr(registry.storage, "Client", lambda project: SimpleNamespace(bucket=str))
    monkeypatch.setattr(registry.storage.Blob, "from_uri", from_uri)
    return ModelRegistry()


def model_text(columns: list[str] = FEATURE_COLUMNS) -> str:
    train = make_features(200, seed=1)
    renamed = train[FEATURE_COLUMNS].set_axis(columns, axis=1)
    model = lgb.LGBMRegressor(n_estimators=5, verbose=-1).fit(renamed, train[LABEL_COLUMN])
    return model.booster_.model_to_string()


def test_load_returns_version_metadata_and_booster(monkeypatch: pytest.MonkeyPatch) -> None:
    files = {"model.txt": model_text(), "metadata.json": json.dumps({"a": 1})}

    champion = fake_registry(monkeypatch, files).load(CHAMPION)

    assert champion.version == "3"
    assert champion.labels == {"run": "run-1"}
    assert champion.created == CREATED
    assert champion.metadata == {"a": 1}
    assert champion.booster.feature_name() == FEATURE_COLUMNS


def test_no_model(monkeypatch: pytest.MonkeyPatch) -> None:
    assert fake_registry(monkeypatch, {}).load(CHAMPION) is None


def test_no_champion_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    files = {"model.txt": model_text(), "metadata.json": "{}"}

    assert fake_registry(monkeypatch, files, alias=False).load(CHAMPION) is None


def test_model_without_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    files = {"model.txt": model_text()}

    assert fake_registry(monkeypatch, files).load(CHAMPION) is None


def test_model_with_other_features(monkeypatch: pytest.MonkeyPatch) -> None:
    other = [f"old_{column}" for column in FEATURE_COLUMNS]
    files = {"model.txt": model_text(other), "metadata.json": "{}"}

    assert fake_registry(monkeypatch, files).load(CHAMPION) is None


def test_used_snapshots_come_from_version_labels(monkeypatch: pytest.MonkeyPatch) -> None:
    labels = {"1": {"snapshot": "features_a"}, "2": {}, "3": {"snapshot": "features_b"}}

    class FakeVersion:
        resource_name = "models/1"

        def __init__(self, name: str) -> None:
            self.labels = labels[name.split("@")[1]]

        @staticmethod
        def list(filter: str) -> list:
            return [FakeVersion]

    class FakeModelRegistry:
        def __init__(self, model: str) -> None:
            pass

        def list_versions(self) -> list[SimpleNamespace]:
            return [SimpleNamespace(version_id=version) for version in labels]

    model_registry = fake_registry(monkeypatch, {})
    monkeypatch.setattr(registry.aiplatform, "Model", FakeVersion)
    monkeypatch.setattr(registry.aiplatform.models, "ModelRegistry", FakeModelRegistry)

    assert model_registry.get_used_snapshots() == {"features_a", "features_b"}
