from datetime import date

import pandas as pd
import requests

from sp500_vol.common.config import get_fred_api_key


class FredClient:
    BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

    def __init__(self) -> None:
        self.api_key = get_fred_api_key()

    def fetch_vix(self, start: date, end: date) -> pd.DataFrame:
        params = {
            "series_id": "VIXCLS",
            "api_key": self.api_key,
            "file_type": "json",
            "observation_start": start.isoformat(),
            "observation_end": end.isoformat(),
        }

        # own errors: API key is in the URL, keep it out of logs
        try:
            response = requests.get(self.BASE_URL, params=params, timeout=30)
        except requests.RequestException as e:
            error_type = type(e).__name__
            raise RuntimeError(f"FRED request failed: {error_type}") from None
        if not response.ok:
            raise RuntimeError(f"FRED request failed with status {response.status_code}")

        data = response.json()
        return to_vix_frame(data["observations"])


def to_vix_frame(observations: list[dict[str, str]]) -> pd.DataFrame:
    df = pd.DataFrame(observations, columns=["date", "value"])
    df = df.rename(columns={"value": "close"})

    df["date"] = pd.to_datetime(df["date"]).dt.date
    # "." = no value
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df = df.dropna(subset=["close"])
    return df
