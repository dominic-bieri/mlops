# S&P 500 Realized Volatility Forecast

MLOps HS26. Predicts how much the S&P 500 will move over the next 5 trading days, updated after each US trading day.
The forecast is the volatility of SPY as a proxy for the S&P 500. It is not a trading signal.

- [Proposal](docs/proposal.pdf)
- [MS2 summary](docs/ms2_summary.pdf)
- [ADRs](docs/adr/)

## Architecture

![System design](docs/media/System_Design.svg)

- Feature pipeline: loads SPY and VIX into BigQuery and builds the `features` table with a versioned snapshot, daily ([`src/sp500_vol/features/`](src/sp500_vol/features/))
- Training pipeline: trains LightGBM on the newest snapshot, registers it in Agent Platform if it beats HAR-RV and the current model, monthly ([`src/sp500_vol/training/`](src/sp500_vol/training/))
- Inference pipeline and UI: MS4

## Changes since the proposal

- Volatility uses open, high, low and close instead of only the close, so the label is less noisy ([ADR 3](docs/adr/0003-volatility-definition.md))
- HAR-RV as a second baseline, VIX corrected by one factor ([ADR 4](docs/adr/0004-baselines.md))
- Retraining monthly instead of weekly ([ADR 6](docs/adr/0006-training-and-retraining.md))
- Success criterion: lower MAE than HAR-RV, instead of 10 % better than the 20-day volatility. The scaled VIX is only reported
- Each `features` version is kept as a BigQuery snapshot with its Git commit ([ADR 2](docs/adr/0002-feature-store.md))
- Terraform for all BigQuery tables, applied by GitHub Actions when a merge to `main` changes `terraform/`

## Requirements

- [Git LFS](https://git-lfs.com)
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
uv run python -m sp500_vol.features.build        # rebuild features
uv run python -m sp500_vol.features.pipeline     # both, as in the image
uv run python -m sp500_vol.training.train        # train and show errors, registers only in GitHub Actions
uv run pytest
```

Runs in GitHub Actions: [features](.github/workflows/feature-pipeline.yml) every morning after a US trading day, [training](.github/workflows/training-pipeline.yml) monthly, both started by [cron-job.org](https://cron-job.org) (ADR 5).

## Backfill

There is no separate backfill script, `ingest` decides on each run what to fetch ([ADR 1](docs/adr/0001-raw-data.md)):

- Table empty: everything from 1993-01-29 (first SPY trading day) until yesterday, New York time
- Table filled: from the latest stored date minus 7 days, only missing days are added
- A skipped run does no harm, the next run fills the gap

## Docker

One `Dockerfile` with two targets, `features` (default) and `training`. [CI](.github/workflows/ci.yml) pushes both to GHCR on every commit to `main`, the pipelines pull the image of their commit.

```bash
docker build --target features -t sp500-vol-features .
docker run --rm --env-file .env \
  -v ~/.config/gcloud/application_default_credentials.json:/creds/adc.json:ro \
  -e GOOGLE_APPLICATION_CREDENTIALS=/creds/adc.json \
  sp500-vol-features
```

Training the same with `--target training`. `.env` and the credentials are only passed at run time, never copied into the image.
