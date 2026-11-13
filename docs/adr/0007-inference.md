# 7. Inference and serving

## Context

One forecast per trading day, after the feature pipeline.
The UI must be public and cost nothing when nobody looks. An Agent Platform endpoint costs about USD 70 per month.

## Decision

- Batch job `predict` at the end of the feature pipeline, as a reusable workflow, so Google accepts the token
- One row per new feature day in `predictions`, the first run only the newest day
- Features come from the `features` table, the same values as in training
- Baselines are fitted at training and saved in `metadata.json` next to the model
- Drift: PSI per feature, last 60 days against the training days, above 0.25 a warning; retraining stays monthly (ADR 6)
- Live errors in the view `prediction_errors`, once the label is known
- Batch prediction only: the forecast needs no input from the request and changes once a day
- API with FastAPI on Cloud Run, 0 to 1 instance, serves the newest row of `predictions` and the registry entry of its model version
- UI with Streamlit as a second Cloud Run service, 0 to 1 instance, only calls the API
- Deploy on every push to `main`: revision without traffic, smoke test, then all traffic

## Consequences

- No cost when idle, the first request waits for the cold start of both services
- An open UI tab keeps a websocket open and the CPU billed, the free tier covers about 50 hours per month
- A new champion shows its first forecast after the next feature run
- The first deploy fails, `predictions` is still empty: run the feature pipeline once, then re-run the deploy job
- A champion without `metadata.json` can't be served, the training pipeline must run once
