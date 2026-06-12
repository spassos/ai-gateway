# Valores de produção usados pelo deploy.yml (terraform apply -var-file=prod.tfvars).
# Não contém segredos — apenas configuração. image_tag vem do input do workflow.
project_id      = "bumblebee-fa6a1"
region          = "us-central1"
vertex_location = "us-east5"

allowed_domain = ""
gateway_users = [
  "sergio.passos88@gmail.com",
]

user_max_budget = 50
