import json
from dataclasses import dataclass

import lightgbm as lgb
from google.api_core.exceptions import NotFound
from google.cloud import aiplatform, storage

from sp500_vol.common.config import get_gcp_project_id, get_gcp_region
from sp500_vol.features.build import FEATURE_COLUMNS

MODEL_NAME = "sp500-vol"
CHAMPION = "champion"
# registry needs an image, inference runs on Cloud Run
SERVING_IMAGE = "us-docker.pkg.dev/cloudrun/container/placeholder:latest"
MODEL_FILE = "model.txt"
METADATA_FILE = "metadata.json"


class ModelRegistry:
    def __init__(self) -> None:
        project = get_gcp_project_id()
        self.client = storage.Client(project=project)
        # created by Terraform (storage.tf)
        self.bucket = self.client.bucket(f"{project}-models")

    def get_parent(self) -> str | None:
        models = aiplatform.Model.list(filter=f'display_name="{MODEL_NAME}"')
        if not models:
            return None
        if len(models) > 1:
            raise RuntimeError(f"{len(models)} models named {MODEL_NAME}, keep one")
        return models[0].resource_name

    def get_champion(self, parent: str | None) -> aiplatform.Model | None:
        if parent is None:
            return None
        try:
            return aiplatform.Model(f"{parent}@{CHAMPION}")
        except NotFound:
            return None

    def load_model(self, registered: aiplatform.Model) -> lgb.Booster:
        return lgb.Booster(model_str=self.download(registered, MODEL_FILE))

    def load_metadata(self, registered: aiplatform.Model) -> dict:
        return json.loads(self.download(registered, METADATA_FILE))

    def download(self, registered: aiplatform.Model, file: str) -> str:
        blob = storage.Blob.from_uri(f"{registered.uri}/{file}", client=self.client)
        return blob.download_as_text()

    def upload(self, path: str, text: str) -> str:
        blob = self.bucket.blob(path)
        blob.upload_from_string(text)
        return f"gs://{self.bucket.name}/{blob.name}"

    def register(
        self,
        model: lgb.LGBMRegressor,
        metadata: dict,
        run_name: str,
        parent: str | None,
        description: str,
        labels: dict[str, str],
    ) -> str:
        self.upload(f"{run_name}/{MODEL_FILE}", model.booster_.model_to_string())
        self.upload(f"{run_name}/{METADATA_FILE}", json.dumps(metadata, indent=2))
        registered = aiplatform.Model.upload(
            display_name=MODEL_NAME,
            artifact_uri=f"gs://{self.bucket.name}/{run_name}",
            serving_container_image_uri=SERVING_IMAGE,
            parent_model=parent,
            version_aliases=[CHAMPION],
            version_description=description,
            labels=labels,
        )
        return registered.version_id


@dataclass
class RegisteredModel:
    version: str
    labels: dict[str, str]
    metadata: dict


# version is a version id or an alias
def get_registered(version: str) -> aiplatform.Model:
    aiplatform.init(project=get_gcp_project_id(), location=get_gcp_region())
    parent = ModelRegistry().get_parent()
    if parent is None:
        raise RuntimeError("no model, run the training pipeline first")
    return aiplatform.Model(f"{parent}@{version}")


def load_registered_model(version: str) -> RegisteredModel:
    registered = get_registered(version)
    metadata = ModelRegistry().load_metadata(registered)
    return RegisteredModel(registered.version_id, dict(registered.labels), metadata)


def load_booster(version: str) -> lgb.Booster:
    registered = get_registered(version)
    booster = ModelRegistry().load_model(registered)
    if booster.feature_name() != FEATURE_COLUMNS:
        raise RuntimeError(f"model {registered.version_id} has other features")
    return booster
