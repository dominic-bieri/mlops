# S&P 500 Realized Volatility Forecast

A project for MLOps HS26.

The goal is to predict how much the S&P 500 will move over the next 5 trading days (realized volatility), updated once per trading day after US market close.

- Proposal: [`docs/proposal.pdf`](docs/proposal.pdf)
- Decisions after the proposal: [`docs/decisions.md`](docs/decisions.md)

## Requirements

This repository uses [Git LFS](https://git-lfs.com) to track PDFs and pictures.

- [uv](https://docs.astral.sh/uv/) for dependency management
- [gcloud CLI](https://cloud.google.com/sdk/docs/install) for Google Cloud access
- [Terraform](https://developer.hashicorp.com/terraform/install) for Google Cloud infrastructure

## Setup

This project uses [uv](https://docs.astral.sh/uv/) for dependency management.

## Configuration

Both files are gitignored. Copy the example file and fill in your values.

| File | Used by | Contains | Template |
|---|---|---|---|
| `.env` | Python code | `FRED_API_KEY`, `TIINGO_API_KEY`, `GCP_PROJECT_ID`, `BQ_DATASET` | `.env.example` |
| `terraform/terraform.tfvars` | Terraform | `project_id` | `terraform/terraform.tfvars.example` |

`BQ_DATASET` in `.env` must match `dataset_id` in Terraform (default `sp500_vol`).

Google Cloud credentials are not stored in the repo, they come from `gcloud auth application-default login`.

## Infrastructure

Google Cloud resources (BigQuery, etc.) are managed with Terraform. See [`terraform/README.md`](terraform/README.md).
