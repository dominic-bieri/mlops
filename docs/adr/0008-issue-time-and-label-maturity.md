# 8. Issue time and label maturity

## Context

A forecast may only use data that was known when it was made.
FRED publishes the VIX of a day only the next morning.

## Decision

- The forecast for a day is made at 13:00 UTC the next morning (Tue–Sat), before the US market opens
- `vix` and `sp500` store `loaded_at`, the time a row was loaded for the first time
- Rows from the first backfill get the time of the backfill
- Training only uses rows with a label, so all 5 future days are known

## Consequences

- No data from the forecast period is used
