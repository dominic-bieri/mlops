import pandas as pd
import requests

from sp500_vol.common.config import get_fred_api_key

FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

response = requests.get(
    FRED_BASE_URL,
    params={
        "series_id": "VIXCLS",
        "api_key": get_fred_api_key(),
        "file_type": "json",
        "sort_order": "desc",
        "limit": 1,
    },
    timeout=10,
)
response.raise_for_status()
df = pd.DataFrame(response.json()["observations"])
print(df)
