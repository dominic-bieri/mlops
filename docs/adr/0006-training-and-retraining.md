# 6. Training and retraining

## Context

The proposal planned weekly retraining and to register the best model, but not how to choose it.
Fixed dates (train until 2020, test from 2024) don't work with monthly retraining: the test set grows and new data never reaches training.

## Decision

- LightGBM with L1 loss, because success is measured with MAE
- Retraining once a month on the newest `features` snapshot (ADR 10), a week only adds 5 rows
- Rolling split: test is the last 12 months, val the 24 months before, train everything before, 5 trading days gap between them
- Number of trees chosen on val, the other parameters are fixed, then trained again on train and val
- Registered only if the test MAE is lower than HAR-RV and the current model
- The current model only counts if it is younger than 6 months, so an old model can't block new ones forever
- Saved as LightGBM text file, so it loads with any LightGBM version
- Each run in Agent Platform Experiments, each registered model a new version of `sp500-vol` in the Model Registry
- Only GitHub Actions logs runs and registers models, local code may not be committed (ADR 10)

## Consequences

- Same code each month, only the dates move
- Test data is never used for training or to choose parameters
- The current model was trained until its own test start, so it has not seen the new test window and the comparison is fair
- The newest 12 months are not in the model
- If the features change or the current model is too old, only HAR-RV counts
- The newest registered version is the default, inference loads it (MS4)
