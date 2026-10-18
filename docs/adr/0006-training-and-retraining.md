# 6. Training and retraining

## Context

The proposal planned weekly retraining and said the best version is registered, but not how it is chosen.

Fixed dates (train until 2020, test from 2024) don't fit a pipeline that retrains every month: the test set grows every day and new data never reaches training.

## Decision

- LightGBM with L1 loss, because success is measured with MAE
- Retraining once a month on the newest `features` snapshot (ADR 10), a week only adds 5 new rows
- Rolling split: test is the last 12 months, val the 24 months before, train everything before, 5 trading days gap between them
- Number of trees chosen on val, other parameters fixed, then trained again on train and val
- Registered only if its MAE on test is lower than HAR-RV and the current default model
- The current model only counts if it is younger than 6 months, so the default is refreshed at least twice a year
- Saved as LightGBM text file, loads with any LightGBM version
- Each run in Agent Platform Experiments, each registered model a new version of `sp500-vol` in the Model Registry

## Consequences

- Same code each month, only the cutoff moves
- The test data is never used for training or to choose parameters
- The current model was trained until its own test start, so it has not seen the new test window and the comparison is fair
- The newest 12 months are not in the model
- If the features change or the current model is too old, only HAR-RV counts
- The default version is the best model, inference loads it (MS4)
