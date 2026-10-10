import os

from dotenv import load_dotenv

load_dotenv()


def get_fred_api_key() -> str:
    return os.environ["FRED_API_KEY"]


def get_tiingo_api_key() -> str:
    return os.environ["TIINGO_API_KEY"]


def get_gcp_project_id() -> str:
    return os.environ["GCP_PROJECT_ID"]


def get_bq_dataset() -> str:
    return os.environ["BQ_DATASET"]
