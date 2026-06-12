# TODO(T-18): serviços Cloud Run.
#
# 1. google_cloud_run_v2_service "gateway" (LiteLLM):
#    - imagem: Artifact Registry construída de gateway/Dockerfile
#    - ingress público (auth é por virtual key no próprio LiteLLM)
#    - env: DATABASE_URL (Cloud SQL), LITELLM_MASTER_KEY (Secret Manager),
#      VERTEX_PROJECT_ID, VERTEX_LOCATION
#    - timeout >= 3600s (streaming de sessões longas de agente)
#    - service account: sa_gateway (roles/aiplatform.user)
#
# 2. google_cloud_run_v2_service "broker":
#    - imagem construída de broker/Dockerfile
#    - SEM allow-unauthenticated: o IAM é a autorização primária (ver iam.tf)
#    - env: LITELLM_BASE_URL (URL interna do gateway), LITELLM_MASTER_KEY,
#      DATABASE_URL, GATEWAY_PUBLIC_URL, BROKER_ALLOWED_DOMAIN
#    - BROKER_DEV_FAKE_AUTH NUNCA setado em produção
