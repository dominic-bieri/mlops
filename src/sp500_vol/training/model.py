import lightgbm as lgb
import pandas as pd

from sp500_vol.features.build import FEATURE_COLUMNS, LABEL_COLUMN

MAX_TREES = 2000


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

    # number of trees chosen on val
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
