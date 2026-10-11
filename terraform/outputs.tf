output "dataset_id" {
  description = "BigQuery dataset ID."
  value       = google_bigquery_dataset.sp500_vol.dataset_id
}
