# Infra do AI Gateway na GCP. Quickstart de deploy em ./README.md.

terraform {
  required_version = ">= 1.7"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
  # Bucket criado pelo infra/bootstrap.sh; nome injetado no init:
  #   terraform init -backend-config="bucket=<TF_STATE_BUCKET>"
  # (Se você já aplicou com state local, acrescente -migrate-state.)
  backend "gcs" {}
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# APIs necessárias. disable_on_destroy=false: destruir a infra não deve
# desligar APIs que outros recursos do projeto possam usar.
resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "sqladmin.googleapis.com",
    "secretmanager.googleapis.com",
    "aiplatform.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
  ])
  service            = each.value
  disable_on_destroy = false
}

resource "google_artifact_registry_repository" "images" {
  repository_id = "ai-gateway"
  location      = var.region
  format        = "DOCKER"
  description   = "Imagens do gateway (litellm) e do broker"
  depends_on    = [google_project_service.apis]
}
