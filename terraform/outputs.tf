output "dataset_id" {
  description = "BigQuery dataset ID."
  value       = google_bigquery_dataset.sp500_vol.dataset_id
}

output "model_bucket" {
  description = "Bucket for registered models."
  value       = google_storage_bucket.models.name
}

output "api_url" {
  description = "Public URL of the API."
  value       = google_cloud_run_v2_service.api.uri
}

output "ui_url" {
  description = "Public URL of the Streamlit UI."
  value       = google_cloud_run_v2_service.ui.uri
}

output "image_repository" {
  description = "Artifact Registry repository for the API image."
  value       = "${google_artifact_registry_repository.images.location}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.images.repository_id}"
}
