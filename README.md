# S&P 500 Realized Volatility Forecast

A project for MLOps HS26.

The goal is to predict how much the S&P 500 will move over the next 5 trading days (realized volatility), updated once per trading day after US market close. See [`docs/proposal.pdf`](docs/proposal.pdf) for the full problem statement, data sources, and system design.

## Requirements

This repository uses [Git LFS](https://git-lfs.com) to track PDFs and pictures.

- [uv](https://docs.astral.sh/uv/) for dependency management
- [gcloud CLI](https://cloud.google.com/sdk/docs/install) for Google Cloud access
- [Terraform](https://developer.hashicorp.com/terraform/install) for Google Cloud infrastructure

## Setup

This project uses [uv](https://docs.astral.sh/uv/) for dependency management.

## Infrastructure

Google Cloud resources (BigQuery, etc.) are managed with Terraform. See [`terraform/README.md`](terraform/README.md).