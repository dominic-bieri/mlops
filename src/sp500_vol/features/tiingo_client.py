from datetime import date

import pandas as pd
import requests

from sp500_vol.common.config import get_tiingo_api_key

TIINGO_BASE_URL = "https://api.tiingo.com/tiingo/daily/SPY/prices"

response = requests.get(
    TIINGO_BASE_URL,
    params={"startDate": date.today().isoformat(), "token": get_tiingo_api_key()},
    timeout=10,
)
response.raise_for_status()
df = pd.DataFrame(response.json())
print(df)
