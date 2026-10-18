# 10. Feature versioning

## Context

`features` is replaced on each run (ADR 5). If a formula changes, the old values are gone.
BigQuery time travel only keeps 7 days.
A model must be traceable to the exact data it was trained on.

## Decision

- After each build, a BigQuery table snapshot of `features`, e.g. `features_20261017_141703` (UTC)
- Description of the snapshot: the Git commit that built it (`GITHUB_SHA`)
- Only GitHub Actions builds a snapshot, local code may not be committed
- No expiration, one version is about 1 MB
- `features` stays the current version, training and inference read it
- Training (MS3) logs the snapshot name, so it can be trained again on the same data
- BigQuery snapshot instead of Parquet on GCS: no extra bucket or roles, same SQL as `features`

## Consequences

- Every feature version ever built can be read again
- Snapshots are read-only, a version can't be changed later
- Snapshots are not in Terraform, the pipeline creates them
- About 250 tables per year in the dataset
