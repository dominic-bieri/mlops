# 5. Feature table

## Context

Features are built from `sp500` and `vix`. The data is small (about 8500 rows).

## Decision

- Compute features in Python (pandas)
- Rebuild the whole `features` table on each run (`WRITE_TRUNCATE_DATA`, keeps schema)
- Volatility in percent per year, like the VIX
- Label in the same table, empty for the last 5 days

## Consequences

- Simple code, easy to test
- Table is replaced in one step, if the load fails the old data stays
- Days without VIX value are dropped, `vix_change_5d` then spans 6 trading days (rare)
