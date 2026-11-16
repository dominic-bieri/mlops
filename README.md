# S&P 500 Realized Volatility Forecast

[![Feature pipeline](https://github.com/dominic-bieri/mlops/actions/workflows/feature-pipeline.yml/badge.svg)](https://github.com/dominic-bieri/mlops/actions/workflows/feature-pipeline.yml)
[![Training pipeline](https://github.com/dominic-bieri/mlops/actions/workflows/training-pipeline.yml/badge.svg)](https://github.com/dominic-bieri/mlops/actions/workflows/training-pipeline.yml)
[![Inference pipeline](https://github.com/dominic-bieri/mlops/actions/workflows/inference-pipeline.yml/badge.svg)](https://github.com/dominic-bieri/mlops/actions/workflows/inference-pipeline.yml)
[![CI](https://github.com/dominic-bieri/mlops/actions/workflows/ci.yml/badge.svg)](https://github.com/dominic-bieri/mlops/actions/workflows/ci.yml)
[![Terraform](https://github.com/dominic-bieri/mlops/actions/workflows/terraform.yml/badge.svg)](https://github.com/dominic-bieri/mlops/actions/workflows/terraform.yml)
[![Render PDF](https://github.com/dominic-bieri/mlops/actions/workflows/render-pdf.yml/badge.svg)](https://github.com/dominic-bieri/mlops/actions/workflows/render-pdf.yml)

MLOps HS26. Forecasts the volatility of the S&P 500 over the next 5 trading days, updated after each US trading day.
SPY is the proxy for the S&P 500. Not a trading signal.

Live: [UI](https://sp500-vol-ui-udjtjgs5dq-oa.a.run.app) · [API](https://sp500-vol-api-udjtjgs5dq-oa.a.run.app/docs). The services start from zero, the first request takes a few seconds.

- [Proposal](docs/proposal.pdf)
- [MS2 summary](docs/ms2_summary.pdf)
- [ADRs](docs/adr/)

## Architecture

![System design](docs/media/System_Design.svg)

- Feature pipeline, daily: loads SPY and VIX into BigQuery, builds the `features` table and a snapshot ([`src/sp500_vol/features/`](src/sp500_vol/features/))
- Training pipeline, monthly: trains LightGBM on the newest snapshot. Registers the model if it beats HAR-RV and is not worse than the current model ([`src/sp500_vol/training/`](src/sp500_vol/training/))
- Inference pipeline, after each feature run: forecasts the new days with `sp500-vol@champion` into `predictions` and checks drift ([`src/sp500_vol/inference/`](src/sp500_vol/inference/), [ADR 7](docs/adr/0007-inference.md))
- API: FastAPI on Cloud Run, serves `predictions`: `/predict`, `/predictions`, `/model`, `/health`
- UI: Streamlit on Cloud Run, calls the API ([`ui/app.py`](ui/app.py))

Only the batch job runs the model. The forecast needs no input and changes once a day, so the API serves the stored rows.

Features, label and table names: [`src/sp500_vol/common/schema.py`](src/sp500_vol/common/schema.py), one place for all three pipelines.

## Module requirements

| Requirement | Where |
|---|---|
| Live data, backfill | [`features/ingest.py`](src/sp500_vol/features/ingest.py), [ADR 1](docs/adr/0001-raw-data.md) |
| Features and feature store | [`features/build.py`](src/sp500_vol/features/build.py), BigQuery `features` with snapshots, [ADR 2](docs/adr/0002-feature-store.md) |
| Training, no leakage | [`training/split.py`](src/sp500_vol/training/split.py), [`training/model.py`](src/sp500_vol/training/model.py), [ADR 6](docs/adr/0006-training-and-retraining.md) |
| Experiment tracking, model registry | Agent Platform, [`training/train.py`](src/sp500_vol/training/train.py), [`common/registry.py`](src/sp500_vol/common/registry.py) |
| Scheduled runs, retraining | [workflows](.github/workflows/) started by cron-job.org, [ADR 5](docs/adr/0005-issue-time-and-label-maturity.md) |
| Inference, UI, cloud deploy | [`inference/`](src/sp500_vol/inference/), [`ui/app.py`](ui/app.py), deploy job in [`ci.yml`](.github/workflows/ci.yml), [ADR 7](docs/adr/0007-inference.md) |
| Model version, drift | `/health`, `/model`, [`inference/drift.py`](src/sp500_vol/inference/drift.py) |
| Tests, Docker, pinned versions | [`tests/`](tests/), [`Dockerfile`](Dockerfile), [`uv.lock`](uv.lock) |
| Infrastructure | [`terraform/`](terraform/), [`docs/google-cloud.md`](docs/google-cloud.md) |

## Pipeline results

Each run shows its result under *Annotations* on its run page, no GitHub login needed. The badges above lead there.

- Feature pipeline: `Features: new snapshot`
- Training pipeline: `Training: new model registered` or `Training: no new model`
- Inference pipeline (started by the feature pipeline): `Inference: new forecast` or `Inference: no new feature day`

## Changes since the proposal

- Volatility uses open, high, low and close instead of only the close, so the label is less noisy ([ADR 3](docs/adr/0003-volatility-definition.md))
- HAR-RV as a second baseline, VIX corrected by one factor ([ADR 4](docs/adr/0004-baselines.md))
- Retraining monthly instead of weekly ([ADR 6](docs/adr/0006-training-and-retraining.md))
- Success: lower MAE than HAR-RV, instead of 10 % better than the 20-day volatility. The scaled VIX is only reported
- Each `features` version is kept as a BigQuery snapshot with its Git commit ([ADR 2](docs/adr/0002-feature-store.md))
- Terraform for all BigQuery tables, applied by GitHub Actions when a merge to `main` changes `terraform/`
- Batch prediction instead of on request ([ADR 7](docs/adr/0007-inference.md))
- Streamlit UI as a second Cloud Run service instead of a page in the API
- No Yahoo Finance backup, Tiingo and FRED were reliable enough

## Requirements

- [Git LFS](https://git-lfs.com) (only for the diagrams)
- [uv](https://docs.astral.sh/uv/)
- [gcloud CLI](https://cloud.google.com/sdk/docs/install)
- [Terraform](https://developer.hashicorp.com/terraform/install)
- [Docker](https://docs.docker.com/get-docker/) (optional, for the image)

## Setup

```bash
uv sync
cp .env.example .env   # fill in your values
gcloud auth application-default login
```

Google Cloud: [`docs/google-cloud.md`](docs/google-cloud.md), then [`terraform/README.md`](terraform/README.md).

## Usage

```bash
uv run python -m sp500_vol.features.ingest       # load VIX and SPY
uv run python -m sp500_vol.features.build        # rebuild features, writes only in GitHub Actions
uv run python -m sp500_vol.features.pipeline     # both, as in the image
uv run python -m sp500_vol.training.train        # train and show errors, registers only in GitHub Actions
uv run python -m sp500_vol.inference.batch       # forecast new days, writes only in GitHub Actions
uv run uvicorn sp500_vol.inference.api:app       # API on http://localhost:8000
uv run streamlit run ui/app.py                   # UI on http://localhost:8501, needs the API
uv run pytest
```

Runs in GitHub Actions: [features](.github/workflows/feature-pipeline.yml) every morning after a US trading day, [training](.github/workflows/training-pipeline.yml) monthly, both started by [cron-job.org](https://cron-job.org) (ADR 5).

## Backfill

There is no separate backfill script, `ingest` decides on each run what to fetch ([ADR 1](docs/adr/0001-raw-data.md)):

- Table empty: everything from 1993-01-29 (first SPY trading day) until yesterday, New York time
- Table filled: from the latest stored date minus 7 days, only missing days are added
- A skipped run does no harm, the next run fills the gap

## Docker

One `Dockerfile` with four targets: `features` (default), `training`, `inference` and `ui`. [CI](.github/workflows/ci.yml) pushes them to GHCR on every commit to `main`. The pipelines pull the image of their commit. CI also deploys `inference` and `ui` to Cloud Run: new revision without traffic, smoke test, then all traffic.

```bash
docker build --target features -t sp500-vol-features .
docker run --rm --env-file .env \
  -v ~/.config/gcloud/application_default_credentials.json:/creds/adc.json:ro \
  -e GOOGLE_APPLICATION_CREDENTIALS=/creds/adc.json \
  sp500-vol-features
```

Training the same with `--target training`. `.env` and the credentials are only passed at run time, never copied into the image.

API and UI together: `docker compose up --build`, UI on http://localhost:8501.

## Rollback

Bad code: give the previous revision all traffic, the same for `sp500-vol-ui`. The next deploy of `main` switches back to the newest revision.

```bash
gcloud run revisions list --service sp500-vol-api --region europe-west6
gcloud run services update-traffic sp500-vol-api --region europe-west6 --to-revisions REVISION=100
```

Bad model: in the Agent Platform Model Registry, set the alias `champion` on the previous version of `sp500-vol`. The next feature run forecasts with it.
