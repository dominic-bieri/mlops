from datetime import date

import pytest
import requests

from sp500_vol.features.fred_client import FredClient, to_vix_frame
from sp500_vol.features.tiingo_client import to_spy_frame


def test_vix_skips_market_holidays() -> None:
    observations = [
        {"date": "2024-01-01", "value": "."},
        {"date": "2024-01-02", "value": "13.20"},
    ]

    df = to_vix_frame(observations)

    assert df.to_dict("records") == [{"date": date(2024, 1, 2), "close": 13.2}]


def test_spy_maps_tiingo_fields_on_ex_dividend_day() -> None:
    prices = [
        {
            "date": "2024-03-15T00:00:00.000Z",
            "open": 510.21,
            "high": 511.70,
            "low": 508.12,
            "close": 509.83,
            "divCash": 1.5949,
        }
    ]

    df = to_spy_frame(prices)

    expected = {
        "date": date(2024, 3, 15),
        "open": 510.21,
        "high": 511.70,
        "low": 508.12,
        "close": 509.83,
        "div_cash": 1.5949,
    }
    assert df.to_dict("records") == [expected]


def test_fred_error_does_not_leak_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FRED_API_KEY", "secret-key")
    response = requests.Response()
    response.status_code = 500
    response.url = "https://api.stlouisfed.org/fred/series/observations?api_key=secret-key"
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: response)

    with pytest.raises(RuntimeError) as error:
        FredClient().fetch_vix(date(2024, 1, 1), date(2024, 1, 2))

    assert "secret-key" not in str(error.value)
    assert "500" in str(error.value)
