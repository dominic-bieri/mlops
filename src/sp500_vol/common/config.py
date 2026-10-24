import logging
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


def is_github_actions() -> bool:
    return os.environ.get("GITHUB_ACTIONS") == "true"


def get_git_commit() -> str:
    return os.environ.get("GITHUB_SHA", "local")


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
