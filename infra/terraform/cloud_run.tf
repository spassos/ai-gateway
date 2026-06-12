locals {
  registry = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.images.repository_id}"
}

resource "google_cloud_run_v2_service" "gateway" {
  name     = "ai-gateway"
  location = var.region
  # Público na camada de rede; auth por virtual key no LiteLLM (ver iam.tf).
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    service_account = google_service_account.gateway.email
    # Sessões de agente com streaming são longas — timeout máximo.
    timeout = "3600s"
    scaling {
      min_instance_count = 0
      max_instance_count = 3
    }

    volumes {
      name = "cloudsql"
      cloud_sql_instance {
        instances = [google_sql_database_instance.main.connection_name]
      }
    }

    containers {
      image = "${local.registry}/gateway:${var.image_tag}"
      ports {
        container_port = 4000
      }
      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
      }
      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }

      env {
        name  = "VERTEX_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "VERTEX_LOCATION"
        value = var.vertex_location
      }
      env {
        name = "LITELLM_MASTER_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.litellm_master_key.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.database_url.secret_id
            version = "latest"
          }
        }
      }

      startup_probe {
        http_get {
          path = "/health/liveliness"
          port = 4000
        }
        initial_delay_seconds = 20
        period_seconds        = 10
        failure_threshold     = 12
      }
    }
  }

  depends_on = [
    google_secret_manager_secret_iam_member.gateway_master_key,
    google_secret_manager_secret_iam_member.gateway_database_url,
  ]
}

resource "google_cloud_run_v2_service" "broker" {
  name     = "ai-gateway-broker"
  location = var.region
  # Público na rede (allUsers em iam.tf); a autorização é no app: token Google
  # verificado + allowlist de e-mails (broker/auth.py), fail-closed.
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    service_account = google_service_account.broker.email
    scaling {
      min_instance_count = 0
      max_instance_count = 2
    }

    volumes {
      name = "cloudsql"
      cloud_sql_instance {
        instances = [google_sql_database_instance.main.connection_name]
      }
    }

    containers {
      image = "${local.registry}/broker:${var.image_tag}"
      ports {
        container_port = 8080
      }
      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }
      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }

      env {
        name  = "LITELLM_BASE_URL"
        value = google_cloud_run_v2_service.gateway.uri
      }
      env {
        name  = "GATEWAY_PUBLIC_URL"
        value = google_cloud_run_v2_service.gateway.uri
      }
      env {
        name  = "BROKER_ALLOWED_DOMAIN"
        value = var.allowed_domain
      }
      env {
        name  = "BROKER_ALLOWED_EMAILS"
        value = join(",", var.gateway_users)
      }
      env {
        name  = "BROKER_USER_MAX_BUDGET"
        value = tostring(var.user_max_budget)
      }
      # BROKER_DEV_FAKE_AUTH NUNCA é setado aqui — só existe no compose local.
      env {
        name = "LITELLM_MASTER_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.litellm_master_key.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.database_url.secret_id
            version = "latest"
          }
        }
      }
    }
  }

  depends_on = [
    google_secret_manager_secret_iam_member.broker_master_key,
    google_secret_manager_secret_iam_member.broker_database_url,
  ]
}
