output "dataset_id" {
  description = "BigQuery dataset ID."
  value       = google_bigquery_dataset.sp500_vol.dataset_id
}

output "dataset_self_link" {
  description = "Self link of the BigQuery dataset."
  value       = google_bigquery_dataset.sp500_vol.self_link
}
