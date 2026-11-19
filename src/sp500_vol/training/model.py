from datetime import date

import lightgbm as lgb
import pandas as pd

from sp500_vol.common.schema import FEATURE_COLUMNS, HORIZON, LABEL_COLUMN

MAX_TREES = 2000
TEST_MONTHS = 12
VAL_MONTHS = 24


def months_before(day: date, months: int) -> date:
    timestamp = pd.Timestamp(day) - pd.DateOffset(months=months)
    return timestamp.date()


def split(features: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    labelled = features.dropna(subset=[LABEL_COLUMN]).sort_values("date")
    test_start = months_before(labelled["date"].max(), TEST_MONTHS)
    val_start = months_before(test_start, VAL_MONTHS)

    # gap of HORIZON rows, so no label reaches into the next window
    train = labelled[labelled["date"] <= val_start].iloc[:-HORIZON]
    in_val = (labelled["date"] > val_start) & (labelled["date"] <= test_start)
    val = labelled[in_val].iloc[:-HORIZON]
    test = labelled[labelled["date"] > test_start]
    return train, val, test


def make_model(trees: int) -> lgb.LGBMRegressor:
    return lgb.LGBMRegressor(
        objective="l1",
        learning_rate=0.02,
        n_estimators=trees,
        random_state=42,
        deterministic=True,
        force_row_wise=True,
        verbose=-1,
    )


def fit_model(train: pd.DataFrame, val: pd.DataFrame) -> lgb.LGBMRegressor:
    model = make_model(MAX_TREES)

    stop = lgb.early_stopping(50, verbose=False)
    model.fit(
        train[FEATURE_COLUMNS],
        train[LABEL_COLUMN],
        eval_X=val[FEATURE_COLUMNS],
        eval_y=val[LABEL_COLUMN],
        eval_metric="l1",
        callbacks=[stop],
    )
    return model


def refit_model(labelled: pd.DataFrame, trees: int) -> lgb.LGBMRegressor:
    model = make_model(trees)
    model.fit(labelled[FEATURE_COLUMNS], labelled[LABEL_COLUMN])
    return model
