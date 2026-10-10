from sp500_vol.common.bigquery import build_merge_sql


def test_merge_matches_on_date_and_only_updates_values() -> None:
    sql = build_merge_sql("p.d.sp500", "p.d.sp500_staging", ["date", "close", "div_cash"])

    assert "ON T.date = S.date" in sql
    assert "UPDATE SET `close` = S.`close`, `div_cash` = S.`div_cash`" in sql
    assert "INSERT (`date`, `close`, `div_cash`) VALUES (`date`, `close`, `div_cash`)" in sql


def test_merge_with_only_date_column_skips_update() -> None:
    sql = build_merge_sql("p.d.days", "p.d.days_staging", ["date"])

    assert "WHEN MATCHED" not in sql
    assert "INSERT (`date`) VALUES (`date`)" in sql
