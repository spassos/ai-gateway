# TODO(T-18): Secret Manager.
#
# - google_secret_manager_secret "litellm_master_key"
#   (gerar valor forte fora do Terraform; nunca em tfvars/state em claro)
# - google_secret_manager_secret "db_password"
# - IAM bindings de acesso apenas para sa_broker e sa_gateway (cada um ao seu)
