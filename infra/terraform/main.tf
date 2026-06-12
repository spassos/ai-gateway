# Infra do AI Gateway — ESQUELETO (T-16). Recursos reais em T-18.
# Ver specs/001-ai-gateway-mvp/plan.md (seção Deploy).

terraform {
  required_version = ">= 1.7"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
  # TODO(T-18): backend gcs para o state.
}

provider "google" {
  project = var.project_id
  region  = var.region
}
