# 8. Issue time and label maturity

## Context

A forecast may only use data that was known when it was made.
FRED usually publishes the VIX of a day the next morning shortly after 9:30 New York time.
GitHub Actions often starts scheduled workflows late or skips them, mostly at the full hour ([GitHub docs](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule), [community discussion](https://github.com/orgs/community/discussions/147369)).
I saw this with my own runs too.

## Decision

- The forecast is made the next morning (Tue–Sat) at 10:17 New York time, after FRED has published the VIX. The market is open by then, but the forecast only uses data up to the previous close
- Cron off the full hour, in New York time, so it stays the same in summer and winter
- `vix` and `sp500` store `loaded_at`, the time a row was loaded for the first time
- Rows from the first backfill get the time of the backfill
- Training only uses rows with a label, so all 5 future days are known

## Consequences

- No data from the forecast period is used
- A late or skipped run does no harm, the next run fills the gap (ADR 2)
- If runs are skipped often, an external scheduler like [cron-job.org](https://cron-job.org) starts the workflow (`workflow_dispatch`)
