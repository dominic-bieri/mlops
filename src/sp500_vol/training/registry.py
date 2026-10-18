import lightgbm as lgb
from google.cloud import aiplatform, storage

from sp500_vol.common.config import get_gcp_project_id, get_model_bucket

MODEL_NAME = "sp500-vol"
# registry needs an image, inference runs on Cloud Run (ADR 1)
SERVING_IMAGE = "us-docker.pkg.dev/cloudrun/container/placeholder:latest"
MODEL_FILE = "model.txt"


class ModelRegistry:
    def __init__(self) -> None:
        self.client = storage.Client(project=get_gcp_project_id())
        self.bucket = self.client.bucket(get_model_bucket())

    def get_current_model(self) -> aiplatform.Model | None:
        models = aiplatform.Model.list(filter=f'display_name="{MODEL_NAME}"')
        if not models:
            return None
        return models[0]

    def load_model(self, registered: aiplatform.Model) -> lgb.Booster | None:
        blob = storage.Blob.from_uri(f"{registered.uri}/{MODEL_FILE}", client=self.client)
        if not blob.exists():
            return None
        return lgb.Booster(model_str=blob.download_as_text())

    def save_file(self, run_name: str, file_name: str, text: str) -> None:
        blob = self.bucket.blob(f"{run_name}/{file_name}")
        blob.upload_from_string(text)

    def register(self, model: lgb.LGBMRegressor, run_name: str, parent: str | None) -> str:
        self.save_file(run_name, MODEL_FILE, model.booster_.model_to_string())
        registered = aiplatform.Model.upload(
            display_name=MODEL_NAME,
            artifact_uri=f"gs://{self.bucket.name}/{run_name}",
            serving_container_image_uri=SERVING_IMAGE,
            parent_model=parent,
        )
        return registered.version_id
