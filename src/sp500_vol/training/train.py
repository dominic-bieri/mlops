import logging
from datetime import UTC, datetime

import lightgbm as lgb
import pandas as pd
from google.cloud import aiplatform
from sklearn.metrics import mean_absolute_error

from sp500_vol.common.bigquery import BigQueryClient
from sp500_vol.common.config import get_gcp_project_id, get_gcp_region, get_git_commit
from sp500_vol.evaluation.baselines import HAR_COLUMNS, fit_har, get_cutoff, split
from sp500_vol.features.build import FEATURE_COLUMNS, LABEL_COLUMN

logger = logging.getLogger(__name__)


def fit_model(train: pd.DataFrame, val: pd.DataFrame) -> lgb.LGBMRegressor:
    model = lgb.LGBMRegressor(
        objective="l1",
        learning_rate=0.02,
        n_estimators=2000,
        random_state=42,
        deterministic=True,
        force_row_wise=True,
        verbose=-1,
    )

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


def log_run(params: dict, metrics: dict) -> str:
    aiplatform.init(
        project=get_gcp_project_id(),
        location=get_gcp_region(),
        experiment="sp500-vol",
        experiment_tensorboard=False,
    )

    run_name = datetime.now(UTC).strftime("run-%Y%m%d-%H%M%S")
    aiplatform.start_run(run_name)
    aiplatform.log_params(params)
    aiplatform.log_metrics(metrics)
    aiplatform.end_run()
    return run_name


def main() -> None:
    bq = BigQueryClient()
    snapshot = bq.get_latest_snapshot("features_")
    features = bq.read_table(snapshot)

    cutoff = get_cutoff(features)
    train, val, test = split(features, cutoff)

    model = fit_model(train, val)
    har = fit_har(train)

    val_prediction = model.predict(val[FEATURE_COLUMNS])
    test_prediction = model.predict(test[FEATURE_COLUMNS])
    har_prediction = har.predict(test[HAR_COLUMNS])

    val_mae = mean_absolute_error(val[LABEL_COLUMN], val_prediction)
    test_mae = mean_absolute_error(test[LABEL_COLUMN], test_prediction)
    har_mae = mean_absolute_error(test[LABEL_COLUMN], har_prediction)
    logger.info("test mae: model %.2f, har_rv %.2f", test_mae, har_mae)

    params = {
        "snapshot": snapshot,
        "git_commit": get_git_commit(),
        "cutoff": str(cutoff),
        "trees": model.best_iteration_,
        "learning_rate": model.learning_rate,
        "num_leaves": model.num_leaves,
        "min_child_samples": model.min_child_samples,
    }
    metrics = {
        "val_mae": val_mae,
        "test_mae": test_mae,
        "har_rv_test_mae": har_mae,
    }
    run_name = log_run(params, metrics)
    logger.info("run: %s", run_name)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
