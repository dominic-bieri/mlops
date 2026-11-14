# 7. Inference and serving

## Context

One forecast per trading day, after the feature pipeline.
The UI must be public and cost nothing when nobody looks. An Agent Platform endpoint costs about USD 70 per month.

## Decision

- Batch job in its own workflow `inference-pipeline`, started by the feature pipeline with `workflow_dispatch` and the commit of its run: own run and badge, same image as the feature run. `workflow_run` is not possible, Google only accepts tokens from `push`, `schedule` and `workflow_dispatch`
- One row per new feature day in `predictions`, the first run only the newest day
- Features come from the `features` table, the same values as in training
- Baselines are fitted at training and saved in `metadata.json` next to the model
- Drift: PSI per feature, last 60 days against the training days; retraining stays monthly (ADR 6)
- Warning when the PSI is above the 95th percentile of all 60-day windows in training, per feature. A fixed 0.25 warned in 57–100 % of past windows: volatility comes in regimes, 60 days in a row never look like 30 years
- Half a count per bin instead of a minimum share, an empty bin added about 0.7 to the PSI
- Live errors: the API joins `predictions` with the label in `features`, once it is known
- Batch prediction only: the forecast needs no input from the request and changes once a day
- API with FastAPI on Cloud Run, 0 to 1 instance, serves the newest row of `predictions` and the registry entry of its model version
- UI with Streamlit as a second Cloud Run service, 0 to 1 instance, only calls the API
- Deploy on every push to `main`: revision without traffic, smoke test, then all traffic
- Smoke test checks the commit and a forecast, not the version behind `@champion`: the API shows the version of the newest forecast, after a promotion it differs until the next feature run

## Consequences

- No cost when idle, the first request waits for the cold start of both services
- An open UI tab keeps a websocket open and the CPU billed, the free tier covers about 50 hours per month
- A new champion shows its first forecast after the next feature run
- A failed inference run doesn't turn the feature run red, only its own badge
- The first deploy fails, `predictions` is still empty: run the feature pipeline once, then re-run the deploy job
- A champion without `metadata.json` can't be served, the training pipeline must run once
