from dataclasses import dataclass

import lightgbm as lgb
from google.cloud import aiplatform

from sp500_vol.common.config import get_gcp_project_id, get_gcp_region
from sp500_vol.features.build import FEATURE_COLUMNS
from sp500_vol.training.registry import CHAMPION, ModelRegistry


@dataclass
class RegisteredModel:
    version: str
    labels: dict[str, str]
    metadata: dict


@dataclass
class Champion(RegisteredModel):
    booster: lgb.Booster


# version is a version id or an alias
def get_registered(version: str) -> tuple[ModelRegistry, aiplatform.Model]:
    aiplatform.init(project=get_gcp_project_id(), location=get_gcp_region())
    registry = ModelRegistry()
    parent = registry.get_parent()
    if parent is None:
        raise RuntimeError("no model, run the training pipeline first")
    return registry, aiplatform.Model(f"{parent}@{version}")


def describe(registry: ModelRegistry, registered: aiplatform.Model) -> RegisteredModel:
    metadata = registry.load_metadata(registered)
    return RegisteredModel(registered.version_id, dict(registered.labels), metadata)


def load_registered_model(version: str) -> RegisteredModel:
    return describe(*get_registered(version))


def load_champion() -> Champion:
    registry, registered = get_registered(CHAMPION)
    booster = registry.load_model(registered)
    if booster.feature_name() != FEATURE_COLUMNS:
        raise RuntimeError(f"champion {registered.version_id} has other features")
    return Champion(**vars(describe(registry, registered)), booster=booster)
