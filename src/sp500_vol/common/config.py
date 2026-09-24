import os

from dotenv import load_dotenv

load_dotenv()


def get_fred_api_key() -> str:
    return os.environ["FRED_API_KEY"]


def get_tiingo_api_key() -> str:
    return os.environ["TIINGO_API_KEY"]
