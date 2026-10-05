variable "project_id" {
  description = "GCP project ID to deploy into."
  type        = string
}

variable "region" {
  description = "GCP region/multi-region for the BigQuery dataset."
  type        = string
  default     = "EU"
}

variable "dataset_id" {
  description = "BigQuery dataset ID (letters, numbers, underscores)."
  type        = string
  default     = "sp500_vol"
}
