# Segredos: gerados pelo Terraform e guardados SÓ no Secret Manager.
# Ficam no tfstate — mantenha o state privado (backend gcs com IAM restrito).

resource "random_password" "litellm_master_key" {
  length  = 40
  special = false
}

resource "google_secret_manager_secret" "litellm_master_key" {
  secret_id = "litellm-master-key"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "litellm_master_key" {
  secret      = google_secret_manager_secret.litellm_master_key.id
  secret_data = "sk-${random_password.litellm_master_key.result}"
}

resource "google_secret_manager_secret" "database_url" {
  secret_id = "ai-gateway-database-url"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "database_url" {
  secret      = google_secret_manager_secret.database_url.id
  secret_data = local.database_url
}
