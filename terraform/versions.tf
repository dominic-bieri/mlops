terraform {
  required_version = ">= 1.9"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 8.0"
    }
  }

  # Bucket name is set at `terraform init` time (see README) since
  # backend config can't reference variables.
  backend "gcs" {}
}

provider "google" {
  project = var.project_id
  region  = var.region
}
