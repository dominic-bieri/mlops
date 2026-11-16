# one place for features, label and tables, used by all three pipelines

HORIZON = 5

FEATURE_COLUMNS = [
    "log_return",
    "abs_log_return",
    "rv_1d",
    "rv_5d",
    "rv_10d",
    "rv_20d",
    "rv_22d",
    "rv_60d",
    "vix",
    "vix_change_5d",
]
LABEL_COLUMN = "rv_next_5d"

# BigQuery tables, created by Terraform (bigquery.tf)
SP500_TABLE = "sp500"
VIX_TABLE = "vix"
FEATURES_TABLE = "features"
PREDICTIONS_TABLE = "predictions"
DRIFT_TABLE = "drift"
SNAPSHOT_PREFIX = "features_"
