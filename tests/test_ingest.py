from datetime import date

import pandas as pd
import pytest

from sp500_vol.features import ingest
from sp500_vol.features.ingest import BACKFILL_START, get_start


class FakeFred:
    def fetch_vix(self, start: date, end: date) -> pd.DataFrame:
        return pd.DataFrame({"date": [date(2024, 3, 15)], "close": [13.2]})


class FailingTiingo:
    def fetch_spy(self, start: date, end: date) -> pd.DataFrame:
        raise RuntimeError("Tiingo down")


class FakeBigQuery:
    def __init__(self) -> None:
        self.written_tables = []

    def get_latest_date(self, table: str) -> date | None:
        return None

    def replace_from(self, df: pd.DataFrame, table: str, start: date) -> None:
        self.written_tables.append(table)


def test_empty_table_starts_at_backfill() -> None:
    start = get_start(None)

    assert start == BACKFILL_START


def test_filled_table_starts_a_week_before_latest_date() -> None:
    start = get_start(date(2024, 3, 15))

    assert start == date(2024, 3, 8)


def test_failed_fetch_writes_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    bq = FakeBigQuery()
    monkeypatch.setattr(ingest, "FredClient", FakeFred)
    monkeypatch.setattr(ingest, "TiingoClient", FailingTiingo)
    monkeypatch.setattr(ingest, "BigQueryClient", lambda: bq)

    with pytest.raises(RuntimeError):
        ingest.main()

    assert bq.written_tables == []
