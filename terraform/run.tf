locals {
  api_name = "sp500-vol-api"
  # created by hand, see docs/google-cloud.md
  api_service_account = "${local.api_name}@${var.project_id}.iam.gserviceaccount.com"
  ui_service_account  = "sp500-vol-ui@${var.project_id}.iam.gserviceaccount.com"
}

resource "google_artifact_registry_repository" "images" {
  project       = var.project_id
  location      = var.model_region
  repository_id = "sp500-vol"
  format        = "DOCKER"

  # 0.5 GB are free
  cleanup_policy_dry_run = false
  cleanup_policies {
    id     = "keep-latest"
    action = "KEEP"
    most_recent_versions {
      keep_count = 2
    }
  }
  # tagged by the deploy job, a rollback needs it
  cleanup_policies {
    id     = "keep-live"
    action = "KEEP"
    condition {
      tag_state    = "TAGGED"
      tag_prefixes = ["live"]
    }
  }
  cleanup_policies {
    id     = "delete-rest"
    action = "DELETE"
    condition {
      tag_state = "ANY"
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_cloud_run_v2_service" "api" {
  project             = var.project_id
  name                = local.api_name
  location            = var.model_region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    service_account = local.api_service_account
    timeout         = "30s"

    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }

    containers {
      # placeholder, ci.yml deploys the image
      image = "us-docker.pkg.dev/cloudrun/container/hello"

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
        cpu_idle          = true
        startup_cpu_boost = true
      }

      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "GCP_REGION"
        value = var.model_region
      }
      env {
        name  = "BQ_DATASET"
        value = google_bigquery_dataset.sp500_vol.dataset_id
      }
    }
  }

  lifecycle {
    ignore_changes = [
      client,
      client_version,
      template[0].containers[0].image,
      traffic,
    ]
  }

  depends_on = [google_project_service.apis]
}

resource "google_cloud_run_v2_service_iam_member" "public" {
  project  = var.project_id
  location = google_cloud_run_v2_service.api.location
  name     = google_cloud_run_v2_service.api.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_service" "ui" {
  project             = var.project_id
  name                = "sp500-vol-ui"
  location            = var.model_region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    service_account = local.ui_service_account
    # Streamlit keeps a websocket open while the page is open
    timeout = "3600s"

    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }

    containers {
      # placeholder, ci.yml deploys the image
      image = "us-docker.pkg.dev/cloudrun/container/hello"

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
        cpu_idle          = true
        startup_cpu_boost = true
      }

      env {
        name  = "API_URL"
        value = google_cloud_run_v2_service.api.uri
      }
    }
  }

  lifecycle {
    ignore_changes = [
      client,
      client_version,
      template[0].containers[0].image,
      traffic,
    ]
  }

  depends_on = [google_project_service.apis]
}

resource "google_cloud_run_v2_service_iam_member" "ui_public" {
  project  = var.project_id
  location = google_cloud_run_v2_service.ui.location
  name     = google_cloud_run_v2_service.ui.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
