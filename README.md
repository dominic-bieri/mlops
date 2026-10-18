# S&P 500 Realized Volatility Forecast

MLOps HS26. Predicts how much the S&P 500 will move over the next 5 trading days, updated after each US trading day.
The forecast is the volatility of SPY as a proxy for the S&P 500. It is not a trading signal.

- [Proposal](docs/proposal.pdf)
- [MS2 summary](docs/ms2_summary.pdf)
- [ADRs](docs/adr/)

## Architecture

![System design](docs/media/System_Design.svg)

- Feature pipeline: loads SPY and VIX into BigQuery and builds the `features` table with a versioned snapshot, daily ([`src/sp500_vol/features/`](src/sp500_vol/features/))
- Training pipeline: trains LightGBM on the newest snapshot, registers it in Agent Platform if it beats HAR-RV, monthly ([`src/sp500_vol/training/`](src/sp500_vol/training/))
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
uv run python -m sp500_vol.evaluation.baselines  # baseline errors per year
uv run python -m sp500_vol.training.train        # train, log run, register if better than HAR-RV
uv run pytest
```

Runs in GitHub Actions: [features](.github/workflows/feature-pipeline.yml) every morning after a US trading day, started by [cron-job.org](https://cron-job.org) (ADR 8), [training](.github/workflows/training-pipeline.yml) monthly.

## Backfill

There is no separate backfill script, `ingest` decides on each run what to fetch ([ADR 1](docs/adr/0001-raw-data.md)):

- Table empty: everything from 1993-01-29 (first SPY trading day) until yesterday, New York time
- Table filled: from the latest stored date minus 7 days, only missing days are added
- A skipped run does no harm, the next run fills the gap

## Docker

No Dockerfile yet. The pipelines run in GitHub Actions with the pinned dependencies from `uv.lock`, an image would add nothing there.
The Dockerfile comes with the inference pipeline and UI on Cloud Run (MS4).
