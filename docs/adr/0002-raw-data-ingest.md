# 2. Raw data ingest

## Context

The project needs daily VIX values (from FRED) and SPY prices (from Tiingo) since 1993.
The two sources do not always have values for the same days, and one source can fail while the other works.
At the start, the tables in BigQuery are empty, so all past data has to be loaded once.
After that, only the newest days are needed.
The proposal planned one table for all data and features, and two scripts: one for the past data and one for the daily update.

## Decision

- Raw data goes into two tables, `vix` and `sp500`, one row per day (`date`)
- Features get their own table ([ADR 5](0005-feature-table.md))
- One ingest script decides on each run what to fetch:
  - Table empty: everything since 1993-01-29 (first SPY trading day)
  - Table filled: only from the latest stored date minus 7 days
- Rows from the start date on are deleted and then loaded again

## Consequences

- If one source fails, nothing is written and the next run catches up
- To build features, the two tables have to be joined on `date`
- No separate script for the past data
- If the job did not run for some days, the next run fills the gap
- FRED sometimes publishes a value one day late, the 7 days overlap picks it up
- Running the script twice does not create duplicates
- If loading fails after the delete, up to 7 days are missing until the next run fills them again
