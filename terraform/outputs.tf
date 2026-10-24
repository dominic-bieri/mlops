output "dataset_id" {
  description = "BigQuery dataset ID."
  value       = google_bigquery_dataset.sp500_vol.dataset_id
}

output "model_bucket" {
  description = "Bucket for registered models."
  value       = google_storage_bucket.models.name
}
