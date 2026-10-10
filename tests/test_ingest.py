from datetime import date

from sp500_vol.features.ingest import BACKFILL_START, get_start


def test_empty_table_starts_at_backfill() -> None:
    start = get_start(None)

    assert start == BACKFILL_START


def test_filled_table_starts_a_week_before_latest_date() -> None:
    start = get_start(date(2024, 3, 15))

    assert start == date(2024, 3, 8)
