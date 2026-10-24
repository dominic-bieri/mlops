# 1. Raw data

## Context

The project needs daily VIX values (FRED) and SPY prices (Tiingo) since 1993.
The two sources don't always have the same days, and one can fail while the other works.
At the start the tables are empty, after that only the newest days are needed.
SPY pays a dividend four times a year, on that day the price drops by about the dividend.
Tiingo's adjusted price (`adjClose`) changes all past prices with every new dividend.

## Decision

- Two tables, `vix` and `sp500`, one row per day (`date`)
- One ingest script decides on each run what to fetch:
  - Table empty: everything since 1993-01-29 (first SPY trading day)
  - Table filled: from the latest stored date minus 7 days
- Only days not yet in the table are added, stored rows are never changed (ADR 5)
- Rows are checked before writing: no missing values, prices above 0, open and close between low and high, no duplicate dates
- Raw prices and the dividend of the day (`div_cash`), not `adjClose`. Returns add the dividend back
- No split correction, SPY never had one

## Consequences

- If a source or a check fails, nothing is written and the next run catches up
- No separate backfill script, a skipped run is filled by the next one
- FRED sometimes publishes a value one day late, the 7 days overlap picks it up
- Running twice creates no duplicates
- Stored prices never change
