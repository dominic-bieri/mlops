resource "google_bigquery_dataset" "sp500_vol" {
  project     = var.project_id
  dataset_id  = var.dataset_id
  location    = var.region
  description = "S&P 500 realized volatility forecast, raw and feature data."

  depends_on = [google_project_service.apis]
}

resource "google_bigquery_table" "vix" {
  project     = var.project_id
  dataset_id  = google_bigquery_dataset.sp500_vol.dataset_id
  table_id    = "vix"
  description = "Daily VIX close from FRED (series VIXCLS)."

  deletion_protection = false

  schema = jsonencode([
    {
      name        = "date"
      type        = "DATE"
      mode        = "REQUIRED"
      description = "Trading day."
    },
    {
      name        = "close"
      type        = "FLOAT64"
      mode        = "REQUIRED"
      description = "VIX closing level."
    },
    {
      name        = "loaded_at"
      type        = "TIMESTAMP"
      mode        = "REQUIRED"
      description = "When the row was first loaded (UTC)."
    },
  ])
}

resource "google_bigquery_table" "sp500" {
  project     = var.project_id
  dataset_id  = google_bigquery_dataset.sp500_vol.dataset_id
  table_id    = "sp500"
  description = "Daily SPY end-of-day prices from Tiingo, used as S&P 500 proxy."

  deletion_protection = false

  schema = jsonencode([
    {
      name        = "date"
      type        = "DATE"
      mode        = "REQUIRED"
      description = "Trading day."
    },
    {
      name        = "open"
      type        = "FLOAT64"
      mode        = "REQUIRED"
      description = "Raw opening price."
    },
    {
      name        = "high"
      type        = "FLOAT64"
      mode        = "REQUIRED"
      description = "Raw daily high."
    },
    {
      name        = "low"
      type        = "FLOAT64"
      mode        = "REQUIRED"
      description = "Raw daily low."
    },
    {
      name        = "close"
      type        = "FLOAT64"
      mode        = "REQUIRED"
      description = "Raw closing price."
    },
    {
      name        = "div_cash"
      type        = "FLOAT64"
      mode        = "REQUIRED"
      description = "Cash dividend paid on this day."
    },
    {
      name        = "loaded_at"
      type        = "TIMESTAMP"
      mode        = "REQUIRED"
      description = "When the row was first loaded (UTC)."
    },
  ])
}

resource "google_bigquery_table" "features" {
  project     = var.project_id
  dataset_id  = google_bigquery_dataset.sp500_vol.dataset_id
  table_id    = "features"
  description = "Daily features and label."

  deletion_protection = false

  schema = jsonencode([
    {
      name        = "date"
      type        = "DATE"
      mode        = "REQUIRED"
      description = "Trading day."
    },
    {
      name        = "log_return"
      type        = "FLOAT64"
      mode        = "REQUIRED"
      description = "Daily log return."
    },
    {
      name        = "abs_log_return"
      type        = "FLOAT64"
      mode        = "REQUIRED"
      description = "Absolute daily log return."
    },
    {
      name        = "rv_1d"
      type        = "FLOAT64"
      mode        = "REQUIRED"
      description = "Volatility of the last day, for HAR-RV."
    },
    {
      name        = "rv_5d"
      type        = "FLOAT64"
      mode        = "REQUIRED"
      description = "Volatility of the last 5 days."
    },
    {
      name        = "rv_10d"
      type        = "FLOAT64"
      mode        = "REQUIRED"
      description = "Volatility of the last 10 days."
    },
    {
      name        = "rv_20d"
      type        = "FLOAT64"
      mode        = "REQUIRED"
      description = "Volatility of the last 20 days, baseline."
    },
    {
      name        = "rv_22d"
      type        = "FLOAT64"
      mode        = "REQUIRED"
      description = "Volatility of the last 22 days, for HAR-RV."
    },
    {
      name        = "rv_60d"
      type        = "FLOAT64"
      mode        = "REQUIRED"
      description = "Volatility of the last 60 days."
    },
    {
      name        = "vix"
      type        = "FLOAT64"
      mode        = "REQUIRED"
      description = "VIX closing level."
    },
    {
      name        = "vix_change_5d"
      type        = "FLOAT64"
      mode        = "REQUIRED"
      description = "VIX change over 5 days."
    },
    {
      name        = "rv_next_5d"
      type        = "FLOAT64"
      mode        = "NULLABLE"
      description = "Label: volatility of the next 5 days."
    },
  ])
}

resource "google_bigquery_table" "predictions" {
  project     = var.project_id
  dataset_id  = google_bigquery_dataset.sp500_vol.dataset_id
  table_id    = "predictions"
  description = "Daily forecasts of the inference pipeline, one row per feature day."

  deletion_protection = false

  schema = jsonencode([
    {
      name        = "date"
      type        = "DATE"
      mode        = "REQUIRED"
      description = "Feature day, the forecast covers the next 5 trading days."
    },
    {
      name        = "horizon_days"
      type        = "INT64"
      mode        = "REQUIRED"
      description = "Trading days ahead."
    },
    {
      name        = "prediction"
      type        = "FLOAT64"
      mode        = "REQUIRED"
      description = "Forecast of the champion."
    },
    {
      name        = "rv_20d"
      type        = "FLOAT64"
      mode        = "REQUIRED"
      description = "Baseline: volatility of the last 20 days."
    },
    {
      name        = "har_rv"
      type        = "FLOAT64"
      mode        = "REQUIRED"
      description = "Baseline: HAR-RV with the coefficients saved at training."
    },
    {
      name        = "vix_scaled"
      type        = "FLOAT64"
      mode        = "REQUIRED"
      description = "Baseline: VIX times the factor saved at training."
    },
    {
      name        = "vix"
      type        = "FLOAT64"
      mode        = "REQUIRED"
      description = "VIX closing level."
    },
    {
      name        = "model_version"
      type        = "STRING"
      mode        = "REQUIRED"
      description = "Model Registry version of the champion."
    },
    {
      name        = "model_run"
      type        = "STRING"
      mode        = "REQUIRED"
      description = "Training run of the champion."
    },
    {
      name        = "git_commit"
      type        = "STRING"
      mode        = "REQUIRED"
      description = "Commit of the inference code."
    },
    {
      name        = "predicted_at"
      type        = "TIMESTAMP"
      mode        = "REQUIRED"
      description = "When the forecast was made (UTC)."
    },
  ])
}

resource "google_bigquery_table" "drift" {
  project     = var.project_id
  dataset_id  = google_bigquery_dataset.sp500_vol.dataset_id
  table_id    = "drift"
  description = "PSI per feature, last 60 days against the training days of the champion."

  deletion_protection = false

  schema = jsonencode([
    {
      name        = "date"
      type        = "DATE"
      mode        = "REQUIRED"
      description = "Newest feature day."
    },
    {
      name        = "feature"
      type        = "STRING"
      mode        = "REQUIRED"
      description = "Feature column."
    },
    {
      name        = "psi"
      type        = "FLOAT64"
      mode        = "REQUIRED"
      description = "Population stability index, above 0.25 is a warning."
    },
    {
      name        = "model_version"
      type        = "STRING"
      mode        = "REQUIRED"
      description = "Champion whose training days are the reference."
    },
    {
      name        = "computed_at"
      type        = "TIMESTAMP"
      mode        = "REQUIRED"
      description = "When the PSI was computed (UTC)."
    },
  ])
}
