# 6. Training and retraining

## Context

The proposal planned weekly retraining and said the best version is registered, but not how it is chosen.

Fixed dates (train until 2020, test from 2024) don't fit a pipeline that retrains every month: the test set grows every day and new data never reaches training.

## Decision

- LightGBM with L1 loss, because success is measured with MAE
- Retraining once a month, a week only adds 5 new rows
- Rolling split: test is the last 12 months, val the 24 months before, train everything before, 5 trading days gap between them
- Number of trees chosen on val (early stopping), other parameters fixed
- A new model is only registered if its MAE on test is lower than HAR-RV
- Trained on the newest `features` snapshot (ADR 10)
- Each run in Agent Platform Experiments: snapshot, Git commit, parameters, MAE on val and test, HAR-RV MAE
- Registered model: new version of `sp500-vol` in the Agent Platform Model Registry, file in the bucket `PROJECT_ID-models`
- Serving image only a placeholder, the registry needs one, inference runs on Cloud Run (ADR 1)
- Monthly GitHub Actions workflow, also manual

## Consequences

- Same code each month, only the cutoff moves
- The test data is never used to choose parameters
- The training workflow runs monthly, not weekly
- Each model can be traced to its run and data, and trained again
- The newest registered version is the default, inference loads it (MS4)
