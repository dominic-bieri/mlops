resource "google_bigquery_dataset" "sp500_vol" {
  project     = var.project_id
  dataset_id  = var.dataset_id
  location    = var.region
  description = "S&P 500 realized volatility forecast — raw and feature data."

  depends_on = [google_project_service.apis]
}

resource "google_bigquery_table" "vix" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.sp500_vol.dataset_id
  table_id   = "vix"

  schema = jsonencode([
    {
      name = "date"
      type = "DATE"
      mode = "REQUIRED"
    },
    {
      name = "value"
      type = "FLOAT64"
      mode = "NULLABLE"
    },
  ])
}
