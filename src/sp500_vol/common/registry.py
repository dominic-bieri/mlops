import json
import logging
from dataclasses import dataclass
from datetime import datetime

import lightgbm as lgb
from google.api_core.exceptions import NotFound
from google.cloud import aiplatform, storage

from sp500_vol.common.config import get_gcp_project_id, get_gcp_region
from sp500_vol.common.schema import FEATURE_COLUMNS

logger = logging.getLogger(__name__)

MODEL_NAME = "sp500-vol"
CHAMPION = "champion"
# registry needs an image, inference runs on Cloud Run
SERVING_IMAGE = "us-docker.pkg.dev/cloudrun/container/placeholder:latest"
MODEL_FILE = "model.txt"
METADATA_FILE = "metadata.json"


@dataclass
class RegisteredModel:
    version: str
    labels: dict[str, str]
    created: datetime
    metadata: dict
    booster: lgb.Booster


class ModelRegistry:
    def __init__(self) -> None:
        project = get_gcp_project_id()
        aiplatform.init(project=project, location=get_gcp_region())
        self.client = storage.Client(project=project)
        # created by Terraform (storage.tf)
        self.bucket = self.client.bucket(f"{project}-models")

    # version is a version id or an alias
    def load(self, version: str) -> RegisteredModel | None:
        parent = self._get_parent()
        if parent is None:
            logger.info("no model %s", MODEL_NAME)
            return None
        try:
            registered = aiplatform.Model(f"{parent}@{version}")
            metadata = json.loads(self._download(registered, METADATA_FILE))
            booster = lgb.Booster(model_str=self._download(registered, MODEL_FILE))
        except NotFound:
            logger.info("model %s@%s or its files not found", MODEL_NAME, version)
            return None
        if booster.feature_name() != FEATURE_COLUMNS:
            logger.info("model %s has other features", registered.version_id)
            return None
        return RegisteredModel(
            registered.version_id,
            dict(registered.labels),
            registered.version_create_time,
            metadata,
            booster,
        )

    def register(
        self,
        model: lgb.LGBMRegressor,
        metadata: dict,
        run_name: str,
        description: str,
        labels: dict[str, str],
    ) -> str:
        self._upload(f"{run_name}/{MODEL_FILE}", model.booster_.model_to_string())
        self._upload(f"{run_name}/{METADATA_FILE}", json.dumps(metadata, indent=2))
        registered = aiplatform.Model.upload(
            display_name=MODEL_NAME,
            artifact_uri=f"gs://{self.bucket.name}/{run_name}",
            serving_container_image_uri=SERVING_IMAGE,
            parent_model=self._get_parent(),
            version_aliases=[CHAMPION],
            version_description=description,
            labels=labels,
        )
        return registered.version_id

    def get_used_snapshots(self) -> set[str]:
        parent = self._get_parent()
        if parent is None:
            return set()
        snapshots = set()
        for info in aiplatform.models.ModelRegistry(parent).list_versions():
            version = aiplatform.Model(f"{parent}@{info.version_id}")
            if "snapshot" in version.labels:
                snapshots.add(version.labels["snapshot"])
        return snapshots

    def _upload(self, path: str, text: str) -> None:
        self.bucket.blob(path).upload_from_string(text)

    def _get_parent(self) -> str | None:
        models = aiplatform.Model.list(filter=f'display_name="{MODEL_NAME}"')
        if not models:
            return None
        if len(models) > 1:
            raise RuntimeError(f"{len(models)} models named {MODEL_NAME}, keep one")
        return models[0].resource_name

    def _download(self, registered: aiplatform.Model, file: str) -> str:
        blob = storage.Blob.from_uri(f"{registered.uri}/{file}", client=self.client)
        return blob.download_as_text()
