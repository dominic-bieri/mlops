# S&P 500 Realized Volatility Forecast

MLOps HS26. Predicts how much the S&P 500 will move over the next 5 trading days, updated after each US trading day.
The forecast is the volatility of SPY as a proxy for the S&P 500. It is not a trading signal.

- [Proposal](docs/proposal.pdf)
- [ADRs](docs/adr/)

## Requirements

[Git LFS](https://git-lfs.com), [uv](https://docs.astral.sh/uv/), [gcloud CLI](https://cloud.google.com/sdk/docs/install), [Terraform](https://developer.hashicorp.com/terraform/install)

## Setup

```bash
uv sync
cp .env.example .env   # fill in your values
gcloud auth application-default login
```

Google Cloud: [`docs/google-cloud.md`](docs/google-cloud.md), then [`terraform/README.md`](terraform/README.md).

## Usage

```bash
uv run python -m sp500_vol.features.ingest   # load VIX and SPY
uv run python -m sp500_vol.features.build    # rebuild features
uv run pytest
```

Runs daily in [GitHub Actions](.github/workflows/feature-pipeline.yml).
