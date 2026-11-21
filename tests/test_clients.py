import threading
from collections.abc import Iterator
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
import requests

from sp500_vol.features import fred_client, tiingo_client
from sp500_vol.features.fred_client import fetch_vix, to_vix_frame
from sp500_vol.features.tiingo_client import fetch_spy, to_spy_frame


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
    monkeypatch.setattr(requests.Session, "get", lambda *args, **kwargs: response)

    with pytest.raises(RuntimeError) as error:
        fetch_vix(date(2024, 1, 1), date(2024, 1, 2))

    assert "secret-key" not in str(error.value)
    assert "500" in str(error.value)


def test_fred_without_json_fails_clearly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FRED_API_KEY", "secret-key")
    response = requests.Response()
    response.status_code = 200
    response._content = b"<html>maintenance</html>"
    monkeypatch.setattr(requests.Session, "get", lambda *args, **kwargs: response)

    with pytest.raises(RuntimeError, match="no observations"):
        fetch_vix(date(2024, 1, 1), date(2024, 1, 2))


@pytest.mark.parametrize("body", [b"null", b"[]", b'{"observations": null}'])
def test_fred_with_wrong_json_fails_clearly(monkeypatch: pytest.MonkeyPatch, body: bytes) -> None:
    monkeypatch.setenv("FRED_API_KEY", "secret-key")
    response = requests.Response()
    response.status_code = 200
    response._content = body
    monkeypatch.setattr(requests.Session, "get", lambda *args, **kwargs: response)

    with pytest.raises(RuntimeError, match="no observations"):
        fetch_vix(date(2024, 1, 1), date(2024, 1, 2))


@pytest.fixture
def flaky_server() -> Iterator[tuple[str, list[int]]]:
    statuses = [502, 200]
    bodies = {
        "/fred": b'{"observations": [{"date": "2024-01-02", "value": "13.20"}]}',
        "/tiingo/SPY/prices": b'[{"date": "2024-01-02T00:00:00.000Z", "open": 1, "high": 1,'
        b' "low": 1, "close": 1, "divCash": 0}]',
    }
    served = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            status = statuses[min(len(served), len(statuses) - 1)]
            served.append(status)
            self.send_response(status)
            self.end_headers()
            if status == 200:
                self.wfile.write(bodies[self.path.split("?")[0]])

        def log_message(self, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}", served
    server.shutdown()


def test_fred_retries_after_502(
    monkeypatch: pytest.MonkeyPatch, flaky_server: tuple[str, list[int]]
) -> None:
    url, served = flaky_server
    monkeypatch.setenv("FRED_API_KEY", "secret-key")
    monkeypatch.setattr(fred_client, "BASE_URL", f"{url}/fred")

    df = fetch_vix(date(2024, 1, 1), date(2024, 1, 2))

    assert served == [502, 200]
    assert df["close"].tolist() == [13.2]


def test_tiingo_retries_after_502(
    monkeypatch: pytest.MonkeyPatch, flaky_server: tuple[str, list[int]]
) -> None:
    url, served = flaky_server
    monkeypatch.setenv("TIINGO_API_KEY", "secret-key")
    monkeypatch.setattr(tiingo_client, "BASE_URL", f"{url}/tiingo")

    df = fetch_spy(date(2024, 1, 1), date(2024, 1, 2))

    assert served == [502, 200]
    assert len(df) == 1
