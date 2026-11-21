# 2. Feature store

## Context

Features are built from `sp500` and `vix`, about 8500 rows.
The label of a day is only known 5 trading days later.
A model must be traceable to the exact data it was trained on, BigQuery time travel only keeps 7 days.

## Decision

- Features in Python (pandas), the whole `features` table is rebuilt on each run (`WRITE_TRUNCATE_DATA`, keeps schema)
- Label in the same table, empty for the last 5 days
- The feature store is the BigQuery `features` table, no extra service (Agent Platform Feature Store would only register the same table)
- After each build a read-only snapshot, e.g. `features_20261017_141703` (UTC), with the Git commit as description
- Before a snapshot the features must have at least 5,000 rows and a row from the last 10 days
- Only GitHub Actions builds a snapshot, local code may not be committed
- `features` stays the current version for inference
- Training reads the newest snapshot and logs its name, so it can be trained again on the same data
- Snapshot instead of Parquet on GCS, so no extra bucket or roles and the same SQL

## Consequences

- A changed formula applies to the whole history, no migration
- Labels of the last 5 days are filled in by a later run
- About 1 MB per snapshot, not in Terraform
- After each run, snapshots are deleted unless a model was trained on it. The newest stays. Older features can be built again from the append-only raw tables
- `vix_change_5d` on SPY trading days, a VIX on a market holiday is ignored
- A SPY day without VIX drops this day and the day 5 later
