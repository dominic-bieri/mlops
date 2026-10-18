resource "google_storage_bucket" "models" {
  project  = var.project_id
  name     = "${var.project_id}-models"
  location = var.model_region

  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  depends_on = [google_project_service.apis]
}
