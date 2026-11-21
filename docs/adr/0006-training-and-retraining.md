# 6. Training and retraining

## Context

The proposal planned weekly retraining and to register the best model, but not how to choose it.
Fixed dates (train until 2020, test from 2024) don't work with monthly retraining. The test set grows and new data never reaches training.

## Decision

- LightGBM with L1 loss, because success is measured with MAE
- Retraining once a month on the newest `features` snapshot (ADR 2). A week only adds 5 rows
- cron-job.org starts it on the 1st at 12:00 New York time, after the feature pipeline (ADR 5)
- Rolling split. Test is the last 12 months, val the 24 months before and train everything before. 5 trading days gap between them
- Val only chooses the number of trees. Then the model is trained again on train and val
- Registered only if the test MAE is lower than HAR-RV and not higher than the current model (alias `champion`) on the same test months. On a tie the newer data wins
- The current model only counts if it is younger than 6 months, so an old model can't block new ones forever
- Saved as LightGBM text file, so it loads with any LightGBM version
- Each run is logged in Agent Platform Experiments, not MLflow or W&B. Same Google Cloud project as data and Model Registry, no own server, no extra login
- Each registered model is a new version of `sp500-vol` in the Model Registry and gets the alias `champion`
- The version stores its run, Git commit and snapshot, so a model leads back to its code and data
- Only GitHub Actions logs runs and registers models, local code may not be committed (ADR 2)

## Consequences

- Same code each month, only the dates move
- Test data is never used for training or to choose parameters
- The current model has not seen the new test window, so the comparison is fair
- The newest 12 months are not in the model
- If the features change or the current model is too old, only HAR-RV counts
- For a rollback, move the alias `champion` back to an older version
