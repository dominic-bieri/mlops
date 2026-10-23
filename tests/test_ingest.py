from datetime import UTC, date, datetime

import pandas as pd
import pytest

from sp500_vol.features import ingest
from sp500_vol.features.ingest import BACKFILL_START, get_end, get_start, only_new


class FakeFred:
    def fetch_vix(self, start: date, end: date) -> pd.DataFrame:
        return pd.DataFrame({"date": [date(2024, 3, 15)], "close": [13.2]})


class BadTiingo:
    def fetch_spy(self, start: date, end: date) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "date": [date(2024, 3, 15)],
                "open": [510.0],
                "high": [505.0],
                "low": [508.0],
                "close": [509.0],
                "div_cash": [0.0],
            }
        )


class FailingTiingo:
    def fetch_spy(self, start: date, end: date) -> pd.DataFrame:
        raise RuntimeError("Tiingo down")


class FakeBigQuery:
    def __init__(self) -> None:
        self.written_tables = []

    def get_dates(self, table: str) -> set[date]:
        return set()

    def append(self, df: pd.DataFrame, table: str) -> None:
        self.written_tables.append(table)


def test_empty_table_starts_at_backfill() -> None:
    start = get_start(None)

    assert start == BACKFILL_START


def test_filled_table_starts_a_week_before_latest_date() -> None:
    start = get_start(date(2024, 3, 15))

    assert start == date(2024, 3, 8)


def test_end_is_the_day_before_in_new_york() -> None:
    end = get_end(datetime(2024, 3, 15, 14, 0, tzinfo=UTC))

    assert end == date(2024, 3, 14)


def test_end_uses_new_york_date_not_utc() -> None:
    end = get_end(datetime(2024, 3, 16, 2, 0, tzinfo=UTC))

    assert end == date(2024, 3, 14)


def test_failed_fetch_writes_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    bq = FakeBigQuery()
    monkeypatch.setattr(ingest, "FredClient", FakeFred)
    monkeypatch.setattr(ingest, "TiingoClient", FailingTiingo)
    monkeypatch.setattr(ingest, "BigQueryClient", lambda: bq)

    with pytest.raises(RuntimeError):
        ingest.main()

    assert bq.written_tables == []


def test_invalid_data_writes_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    bq = FakeBigQuery()
    monkeypatch.setattr(ingest, "FredClient", FakeFred)
    monkeypatch.setattr(ingest, "TiingoClient", BadTiingo)
    monkeypatch.setattr(ingest, "BigQueryClient", lambda: bq)

    with pytest.raises(ValueError):
        ingest.main()

    assert bq.written_tables == []


def test_stored_days_are_not_loaded_again() -> None:
    df = pd.DataFrame({"date": [date(2024, 3, 14), date(2024, 3, 15)], "close": [13.0, 13.2]})
    loaded_at = pd.Timestamp("2024-03-16 13:00", tz="UTC")

    new = only_new(df, {date(2024, 3, 14)}, loaded_at)

    assert new["date"].tolist() == [date(2024, 3, 15)]
    assert new["loaded_at"].tolist() == [loaded_at]
