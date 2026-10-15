# 5. Feature table

## Context

Features are built from `sp500` and `vix`. The data is small (about 8500 rows).
The label of a day is only known 5 trading days later.

## Decision

- Compute features in Python (pandas)
- Rebuild the whole `features` table on each run (`WRITE_TRUNCATE_DATA`, keeps schema)
- Volatility in percent per year, like the VIX
- Label in the same table, empty for the last 5 days
- Feature store: the BigQuery `features` table, used by training and inference
- No extra feature store service (e.g. Agent Platform Feature Store): offline only, it would just register the same table

## Consequences

- Table is replaced in one step, if the load fails the old data stays
- Labels of the last 5 days are filled in by a later run, no single rows have to be updated
- A changed formula applies to the whole history, no migration needed
- Prices are fetched from the APIs only once, then read from the raw tables (ADR 2)
- Days without VIX value are dropped, `vix_change_5d` then spans 6 trading days (rare)
- Past days get the same values on each rebuild, as long as the code doesn't change
