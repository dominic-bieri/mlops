# S&P 500 Realized Volatility Forecast

[![Feature pipeline](https://github.com/dominic-bieri/mlops/actions/workflows/feature-pipeline.yml/badge.svg)](https://github.com/dominic-bieri/mlops/actions/workflows/feature-pipeline.yml)
[![Training pipeline](https://github.com/dominic-bieri/mlops/actions/workflows/training-pipeline.yml/badge.svg)](https://github.com/dominic-bieri/mlops/actions/workflows/training-pipeline.yml)
[![Inference pipeline](https://github.com/dominic-bieri/mlops/actions/workflows/inference-pipeline.yml/badge.svg)](https://github.com/dominic-bieri/mlops/actions/workflows/inference-pipeline.yml)
[![CI](https://github.com/dominic-bieri/mlops/actions/workflows/ci.yml/badge.svg)](https://github.com/dominic-bieri/mlops/actions/workflows/ci.yml)

MLOps HS26. Forecasts the volatility of the S&P 500 over the next 5 trading days, updated after each US trading day.
SPY is the proxy for the S&P 500. Not a trading signal.

Live: [UI](https://sp500-vol-ui-udjtjgs5dq-oa.a.run.app) · [API](https://sp500-vol-api-udjtjgs5dq-oa.a.run.app/docs). The services start from zero, the first request takes a few seconds.

- [Proposal](docs/proposal.pdf)
- [MS2 summary](docs/ms2_summary.pdf)
- [ADRs](docs/adr/)

## Architecture

![System design](docs/media/System_Design.svg)

- Feature pipeline, daily: loads SPY and VIX into BigQuery, builds the `features` table and a snapshot ([`features/`](src/sp500_vol/features/), [ADR 1](docs/adr/0001-raw-data.md), [ADR 2](docs/adr/0002-feature-store.md))
- Training pipeline, monthly: trains LightGBM on the newest snapshot, registers it if it beats HAR-RV ([`training/`](src/sp500_vol/training/), [ADR 6](docs/adr/0006-training-and-retraining.md))
- Inference pipeline, after each feature run: forecasts the new days with `sp500-vol@champion` and checks drift ([`inference/`](src/sp500_vol/inference/), [ADR 7](docs/adr/0007-inference.md))
- API and UI on Cloud Run, the API serves the stored forecasts ([`ui/app.py`](ui/app.py))

Features, label and table names for all three pipelines: [`common/schema.py`](src/sp500_vol/common/schema.py).

## Pipeline results

Each run writes its result to the job summary of its run page, the badges above lead there. Needs a GitHub login, no Google Cloud access.

## Requirements

- [Git LFS](https://git-lfs.com) (diagrams and PDFs)
- [uv](https://docs.astral.sh/uv/)
- [gcloud CLI](https://cloud.google.com/sdk/docs/install)
- [Terraform](https://developer.hashicorp.com/terraform/install)
- [Docker](https://docs.docker.com/get-docker/) (optional)

## Setup

```bash
uv sync
cp .env.example .env   # fill in your values
gcloud auth application-default login
```

Google Cloud: [`docs/google-cloud.md`](docs/google-cloud.md), then [`terraform/README.md`](terraform/README.md).

## Usage

```bash
uv run python -m sp500_vol.features.pipeline     # load VIX and SPY, build features
uv run python -m sp500_vol.training.train        # train and show errors
uv run python -m sp500_vol.inference.batch       # forecast new days
uv run uvicorn sp500_vol.inference.api:app       # API on http://localhost:8000
uv run streamlit run ui/app.py                   # UI on http://localhost:8501, needs the API
uv run pytest
```

Local runs only read, only GitHub Actions writes (ADR 2). The pipelines are started by [cron-job.org](https://cron-job.org): features every day, training monthly (ADR 5).
Backfill: an empty table is filled from 1993, a skipped run is filled by the next one ([ADR 1](docs/adr/0001-raw-data.md)).

## Docker

One [`Dockerfile`](Dockerfile) with the targets `features`, `training`, `inference` and `ui`. CI pushes them to GHCR and deploys `inference` and `ui` to Cloud Run.

```bash
docker build --target features -t sp500-vol-features .
docker run --rm --env-file .env \
  -v ~/.config/gcloud/application_default_credentials.json:/creds/adc.json:ro \
  -e GOOGLE_APPLICATION_CREDENTIALS=/creds/adc.json \
  sp500-vol-features
```

API and UI together: `docker compose up --build`.

## Rollback

- Code: `gcloud run services update-traffic sp500-vol-api --region europe-west6 --to-revisions REVISION=100`, the same for `sp500-vol-ui`
- Model: set the alias `champion` on the previous version of `sp500-vol` in the Model Registry
