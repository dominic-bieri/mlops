import lightgbm as lgb
from google.api_core.exceptions import NotFound
from google.cloud import aiplatform, storage

from sp500_vol.common.config import get_gcp_project_id

MODEL_NAME = "sp500-vol"
CHAMPION = "champion"
# registry needs an image, inference runs on Cloud Run
SERVING_IMAGE = "us-docker.pkg.dev/cloudrun/container/placeholder:latest"
MODEL_FILE = "model.txt"


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
        return models[0].resource_name

    def get_champion(self, parent: str | None) -> aiplatform.Model | None:
        if parent is None:
            return None
        try:
            return aiplatform.Model(f"{parent}@{CHAMPION}")
        except NotFound:
            return None

    def load_model(self, registered: aiplatform.Model) -> lgb.Booster:
        blob = storage.Blob.from_uri(f"{registered.uri}/{MODEL_FILE}", client=self.client)
        return lgb.Booster(model_str=blob.download_as_text())

    def register(
        self, model: lgb.LGBMRegressor, run_name: str, parent: str | None, description: str
    ) -> str:
        blob = self.bucket.blob(f"{run_name}/{MODEL_FILE}")
        blob.upload_from_string(model.booster_.model_to_string())
        registered = aiplatform.Model.upload(
            display_name=MODEL_NAME,
            artifact_uri=f"gs://{self.bucket.name}/{run_name}",
            serving_container_image_uri=SERVING_IMAGE,
            parent_model=parent,
            version_aliases=[CHAMPION],
            version_description=description,
        )
        return registered.version_id
