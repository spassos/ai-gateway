# TODO(T-18): IAM — o coração do modelo de segurança (ver plan.md).
#
# 1. google_service_account "sa_gateway"
#    + google_project_iam_member roles/aiplatform.user
#      (acesso aos modelos do Vertex; é a ÚNICA credencial de provedor do sistema)
#
# 2. google_service_account "sa_broker"
#    + roles/secretmanager.secretAccessor no secret do LITELLM_MASTER_KEY
#
# 3. AUTORIZAÇÃO DOS DEVS — obrigatório, sem isso o gcloud auth é uma brecha:
#    google_cloud_run_v2_service_iam_member:
#      service = broker
#      role    = "roles/run.invoker"
#      member  = var.dev_group   # ex.: group:ai-gateway-users@empresa.com
#    O smoke de produção DEVE confirmar 403 para conta fora do grupo (T-18).
