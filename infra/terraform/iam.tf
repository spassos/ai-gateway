# IAM — o coração do modelo de segurança (ver specs/001 plan.md).

# SA do gateway (LiteLLM): a ÚNICA credencial de provedor do sistema.
resource "google_service_account" "gateway" {
  account_id   = "ai-gateway-litellm"
  display_name = "AI Gateway - LiteLLM proxy"
}

resource "google_project_iam_member" "gateway_vertex" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.gateway.email}"
}

resource "google_project_iam_member" "gateway_cloudsql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.gateway.email}"
}

# SA do broker: acessa segredos e o banco; nada de Vertex.
resource "google_service_account" "broker" {
  account_id   = "ai-gateway-broker"
  display_name = "AI Gateway - broker de identidade"
}

resource "google_project_iam_member" "broker_cloudsql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.broker.email}"
}

resource "google_secret_manager_secret_iam_member" "gateway_master_key" {
  secret_id = google_secret_manager_secret.litellm_master_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.gateway.email}"
}

resource "google_secret_manager_secret_iam_member" "broker_master_key" {
  secret_id = google_secret_manager_secret.litellm_master_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.broker.email}"
}

resource "google_secret_manager_secret_iam_member" "gateway_database_url" {
  secret_id = google_secret_manager_secret.database_url.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.gateway.email}"
}

resource "google_secret_manager_secret_iam_member" "broker_database_url" {
  secret_id = google_secret_manager_secret.database_url.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.broker.email}"
}

# Broker público na camada de rede (allUsers), como o gateway. A AUTORIZAÇÃO
# real é no app (broker/auth.py): valida a assinatura do ID token do Google
# (JWKS), email_verified e a allowlist BROKER_ALLOWED_EMAILS (= gateway_users),
# fail-closed. Por que não run.invoker por usuário? O `gcloud auth
# print-identity-token` de conta de usuário emite token com audience fixo (o
# client do gcloud), que o IAM do Cloud Run rejeita (precisa de audience = URL
# do serviço) — inviabilizaria o login em um comando. Trocar provedor de
# autorização da borda (IAM) para o app (allowlist) é o que permite o fluxo
# "gcloud auth + CLI funciona". A brecha do "qualquer conta Google" continua
# fechada: sem e-mail na allowlist, o broker nega (403).
resource "google_cloud_run_v2_service_iam_member" "broker_public" {
  name     = google_cloud_run_v2_service.broker.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# O gateway (LiteLLM) é público na camada IAM: a autenticação é por virtual
# key dentro do próprio LiteLLM (mesmo modelo de qualquer API SaaS com key).
resource "google_cloud_run_v2_service_iam_member" "gateway_public" {
  name     = google_cloud_run_v2_service.gateway.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}
