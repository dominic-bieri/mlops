from datetime import date
from typing import Any

import pandas as pd

from sp500_vol.common.config import get_tiingo_api_key
from sp500_vol.features.http import get_session

BASE_URL = "https://api.tiingo.com/tiingo/daily"


def fetch_spy(start: date, end: date) -> pd.DataFrame:
    url = f"{BASE_URL}/SPY/prices"
    params = {
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
    }
    # header keeps token out of logs
    headers = {"Authorization": f"Token {get_tiingo_api_key()}"}

    with get_session() as session:
        response = session.get(url, params=params, headers=headers, timeout=30)
    response.raise_for_status()

    data = response.json()
    return to_spy_frame(data)


def to_spy_frame(prices: list[dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(prices, columns=["date", "open", "high", "low", "close", "divCash"])
    df = df.rename(columns={"divCash": "div_cash"})

    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df
