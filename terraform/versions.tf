terraform {
  required_version = ">= 1.9"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 8.0"
    }
  }

  # bucket set at terraform init, see README
  backend "gcs" {}
}

provider "google" {
  project = var.project_id
  region  = var.region
}
