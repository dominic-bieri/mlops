# 9. Training and retraining

## Context

The proposal planned weekly retraining and said the best version is registered, but not how it is chosen.

## Decision

- LightGBM with L1 loss, because success is measured with MAE
- Parameters from a small grid, trained until 2020 and validated on 2021 to 2023
- Test from 2024 once, with a fixed model trained until 2023
- Retraining once a month, a week only adds 5 new rows
- A new model is trained on all data except the last 3 months
- It replaces the current model only if its MAE on these 3 months is lower than the current model, HAR-RV and the scaled VIX (ADR 7)
- If it does, it is trained again on all data with the same parameters before it is registered

## Consequences

- The test data is never used to choose parameters
- The training workflow runs monthly, not weekly
