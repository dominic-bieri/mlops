# 7. Inference and serving

## Context

One forecast per trading day, after the feature pipeline.
The UI must be public and cost nothing when nobody looks. An Agent Platform endpoint costs about USD 70 per month.

## Decision

- Batch prediction only: the forecast needs no input from the request and changes once a day
- Own workflow `inference-pipeline`, started by the feature pipeline with `workflow_dispatch`. `workflow_run` is not possible, Google only accepts tokens from `push`, `schedule` and `workflow_dispatch`
- One row in `predictions` per feature day after `train_end` of the champion. A missed run is caught up
- Days before the first live forecast are marked `backfill`: the test period, forecast later, so the chart has history. The live MAE leaves them out
- Features come from the `features` table, the same values as in training
- Baselines are fitted at training and saved in `metadata.json` next to the model
- Drift: PSI per feature, last 60 days against the training days. Retraining stays monthly (ADR 6)
- Warning when the PSI is above the 95th percentile of all 60-day windows in training. A fixed 0.25 warned in 57–100 % of past windows, because volatility comes in regimes
- Live errors: the API joins `predictions` with the label in `features`, once it is known
- API: FastAPI on Cloud Run, serves `predictions` and the registry entry of the model version
- UI: Streamlit as a second Cloud Run service, only calls the API
- Both scale from 0 to 1 instance
- Deploy on every push to `main`: revision without traffic, smoke test, then all traffic
- The smoke test checks the commit and a forecast, not the champion version. The API shows the version of the newest forecast, it changes with the next feature run

## Consequences

- No cost when idle, the first request waits for the cold start of both services
- An open UI tab keeps the CPU billed, the free tier covers about 50 hours per month
- A new champion shows its first forecast after the next feature run
- A failed inference run only turns its own badge red, not the feature run
- The first deploy fails because `predictions` is empty: run the feature pipeline once, then re-run the deploy job
- A champion without `metadata.json` can't be served
