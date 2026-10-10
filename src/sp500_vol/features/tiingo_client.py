from datetime import date
from typing import Any

import pandas as pd
import requests

from sp500_vol.common.config import get_tiingo_api_key


class TiingoClient:
    BASE_URL = "https://api.tiingo.com/tiingo/daily"

    def __init__(self) -> None:
        self.api_key = get_tiingo_api_key()

    def fetch_spy(self, start: date, end: date) -> pd.DataFrame:
        url = f"{self.BASE_URL}/SPY/prices"
        params = {
            "startDate": start.isoformat(),
            "endDate": end.isoformat(),
        }
        # token in header, keeps it out of logs
        headers = {"Authorization": f"Token {self.api_key}"}

        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()

        data = response.json()
        return to_spy_frame(data)


def to_spy_frame(prices: list[dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(prices, columns=["date", "close", "divCash"])
    df = df.rename(columns={"divCash": "div_cash"})

    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df["div_cash"] = pd.to_numeric(df["div_cash"], errors="coerce")
    df["div_cash"] = df["div_cash"].fillna(0.0)

    df = df.dropna(subset=["close"])
    return df
