# 8. Issue time and label maturity

## Context

A forecast may only use data that was known when it was made.
FRED usually publishes the VIX of a day the next morning shortly after 9:30 New York time.
GitHub Actions often starts scheduled workflows late or skips them ([GitHub docs](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule), [community discussion](https://github.com/orgs/community/discussions/207346)).
My runs started 3–5 hours late, one was skipped.
Runs started with `workflow_dispatch` start within seconds.

## Decision

- The forecast is made the next morning (Tue–Sat) at 10:00 New York time, after FRED has published the VIX. The market is open by then, but the forecast only uses data up to the previous close
- The time is set in New York time, so it stays the same in summer and winter
- Ingest only fetches days up to yesterday in New York time, a row of the running day could be intraday and would never be corrected (ADR 2)
- [cron-job.org](https://cron-job.org) starts the workflow with `workflow_dispatch`, no `schedule` in the workflow
- Fine-grained token for cron-job.org: only this repo, only `Actions: write`, expires after a year
- `vix` and `sp500` store `loaded_at`, the time a row was loaded for the first time
- Rows from the first backfill get the time of the backfill
- Training only uses rows with a label, so all 5 future days are known

## Consequences

- No data from the forecast period is used
- A late or skipped run does no harm, the next run fills the gap (ADR 2)
- The schedule is no longer in the repo (ADR 1), it lives in cron-job.org
- A leaked token can start, cancel or delete runs, but can't read code or secrets or reach Google Cloud
- The token has to be renewed once a year
