# Copie para terraform.tfvars (gitignored) e ajuste.
project_id = "igneous-primacy-488819-g4"
region     = "us-central1"

# Modelos Claude (parceiros) não estão em todas as regiões; us-east5/global
# são as usuais. Gemini existe em ambas.
vertex_location = "us-east5"

# Sem Google Workspace: autorização por allowlist de e-mails.
allowed_domain = ""
gateway_users = [
  "sergio.passos88@gmail.com",
]

user_max_budget = 50

# Tag criada pelo `make push-images TAG=v0.1.0`
image_tag = "v0.1.0"
