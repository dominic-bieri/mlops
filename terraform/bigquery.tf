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
  ])
}

resource "google_bigquery_table" "sp500" {
  project     = var.project_id
  dataset_id  = google_bigquery_dataset.sp500_vol.dataset_id
  table_id    = "sp500"
  description = "Daily SPY end-of-day prices from Tiingo, used as S&P 500 proxy."

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
      description = "Raw closing price."
    },
    {
      name        = "div_cash"
      type        = "FLOAT64"
      mode        = "REQUIRED"
      description = "Cash dividend paid on this day."
    },
  ])
}

resource "google_bigquery_table" "features" {
  project     = var.project_id
  dataset_id  = google_bigquery_dataset.sp500_vol.dataset_id
  table_id    = "features"
  description = "Daily features and label."

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
