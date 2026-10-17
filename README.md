# S&P 500 Realized Volatility Forecast

MLOps HS26. Predicts how much the S&P 500 will move over the next 5 trading days, updated after each US trading day.
The forecast is the volatility of SPY as a proxy for the S&P 500. It is not a trading signal.

- [Proposal](docs/proposal.pdf)
- [MS2 summary](docs/ms2_summary.pdf)
- [ADRs](docs/adr/)

## Architecture

![System design](docs/media/System_Design.svg)

- Feature pipeline: loads SPY and VIX into BigQuery and builds the `features` table, daily ([`src/sp500_vol/features/`](src/sp500_vol/features/))
- Training pipeline: MS3
- Inference pipeline and UI: MS4

## Changes since the proposal

- Volatility uses open, high, low and close instead of only the close, so the label is less noisy ([ADR 6](docs/adr/0006-volatility-definition.md))
- HAR-RV as a second baseline, VIX corrected by one factor ([ADR 7](docs/adr/0007-baselines.md))
- Retraining monthly instead of weekly ([ADR 9](docs/adr/0009-training-and-retraining.md))
- Success criterion: lower MAE than HAR-RV, instead of 10 % better than the 20-day volatility. The scaled VIX is only reported
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
uv run pytest
```

Runs daily in [GitHub Actions](.github/workflows/feature-pipeline.yml).
