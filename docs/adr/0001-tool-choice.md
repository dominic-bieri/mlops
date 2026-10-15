# 1. Tool choice

## Context

For each tool, one reason why it was chosen and not an alternative.

## Decision

- BigQuery instead of Cloud SQL: no database server to run, free at this size
- Agent Platform (Vertex AI) instead of MLflow or W&B: same Google Cloud project and login, no extra server or account
- GitHub Actions instead of Cloud Scheduler or Airflow: code and schedule in the same repo, already used for the tests
- FastAPI on Cloud Run instead of an Agent Platform endpoint: Cloud Run stops when there are no requests, an endpoint always runs and costs money
- LightGBM instead of a neural network (e.g. LSTM): works well on small tabular data, trains in seconds without a GPU
- Terraform instead of setting up resources in the console: tables and roles are in the repo and deployed by GitHub Actions
