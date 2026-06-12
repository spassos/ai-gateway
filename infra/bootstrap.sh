#!/usr/bin/env bash
# Bootstrap único do deploy via GitHub Actions (rodar UMA vez, como dono do
# projeto). Cria o que o CI não pode criar para si mesmo:
#   1. bucket GCS para o state do Terraform
#   2. service account de deploy (poderosa — ver aviso no fim)
#   3. Workload Identity Federation restrita a este repositório
#   4. (opcional) variáveis de repositório no GitHub via gh CLI
#
# Por que manual e não no CI?
#   Problema galinha-e-ovo: o CI autentica no GCP via WIF, mas é este script
#   que cria o WIF. Sem credencial GCP não há CI; sem CI há este script.
#   Roda UMA VEZ da sua máquina já autenticada com `gcloud auth login`.
#
# Por que o Model Garden (habilitar Claude) é permanentemente manual?
#   O Google exige aceite dos Termos de Serviço por projeto via Console. Não
#   existe API para aceitar termos de parceiro programaticamente.
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-igneous-primacy-488819-g4}"
REGION="${REGION:-us-central1}"
GITHUB_REPO="${GITHUB_REPO:-spassos/ai-gateway}"
STATE_BUCKET="${STATE_BUCKET:-${PROJECT_ID}-tfstate}"
SA_NAME="ai-gateway-deployer"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
POOL_ID="github-actions"
PROVIDER_ID="github"

gcloud config set project "$PROJECT_ID"
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')

echo "==> 1/4 APIs base"
gcloud services enable iamcredentials.googleapis.com sts.googleapis.com \
  cloudresourcemanager.googleapis.com storage.googleapis.com

echo "==> 2/4 Bucket de state: gs://${STATE_BUCKET}"
gcloud storage buckets create "gs://${STATE_BUCKET}" --location="$REGION" \
  --uniform-bucket-level-access 2>/dev/null || echo "    (já existe)"
gcloud storage buckets update "gs://${STATE_BUCKET}" --versioning

echo "==> 3/4 Service account de deploy: ${SA_EMAIL}"
gcloud iam service-accounts create "$SA_NAME" \
  --display-name="AI Gateway deployer (GitHub Actions)" 2>/dev/null || echo "    (já existe)"

# Papéis que o terraform apply precisa. projectIamAdmin é o mais sensível
# (gerencia bindings) — por isso a WIF abaixo restringe o uso desta SA à
# branch main DESTE repositório. artifactregistry.admin cobre o push das
# imagens (build é no runner, não no Cloud Build).
for role in \
  roles/run.admin \
  roles/cloudsql.admin \
  roles/secretmanager.admin \
  roles/artifactregistry.admin \
  roles/iam.serviceAccountAdmin \
  roles/iam.serviceAccountUser \
  roles/serviceusage.serviceUsageAdmin \
  roles/storage.admin \
  roles/resourcemanager.projectIamAdmin; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${SA_EMAIL}" --role="$role" --condition=None --quiet > /dev/null
  echo "    + $role"
done

echo "==> 4/4 Workload Identity Federation (repo ${GITHUB_REPO}, branch main)"
gcloud iam workload-identity-pools create "$POOL_ID" --location=global \
  --display-name="GitHub Actions" 2>/dev/null || echo "    (pool já existe)"
gcloud iam workload-identity-pools providers create-oidc "$PROVIDER_ID" \
  --location=global --workload-identity-pool="$POOL_ID" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
  --attribute-condition="assertion.repository == '${GITHUB_REPO}' && assertion.ref == 'refs/heads/main'" \
  2>/dev/null || echo "    (provider já existe)"

gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/attribute.repository/${GITHUB_REPO}" \
  --quiet > /dev/null

WIF_PROVIDER="projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/providers/${PROVIDER_ID}"

# Configura variáveis no GitHub automaticamente se o gh CLI estiver disponível
# e autenticado. Caso contrário imprime os valores para copiar manualmente.
echo ""
if command -v gh &>/dev/null && gh auth status &>/dev/null 2>&1; then
  echo "==> 5/5 Variáveis do GitHub (via gh CLI)"
  gh variable set GCP_WIF_PROVIDER --body "$WIF_PROVIDER"        --repo "$GITHUB_REPO"
  gh variable set GCP_DEPLOYER_SA  --body "$SA_EMAIL"            --repo "$GITHUB_REPO"
  gh variable set TF_STATE_BUCKET  --body "$STATE_BUCKET"        --repo "$GITHUB_REPO"
  echo "    GCP_WIF_PROVIDER, GCP_DEPLOYER_SA, TF_STATE_BUCKET configurados."
  echo ""
  echo "Bootstrap concluído. Único passo manual restante:"
  echo ""
  echo "  Vertex AI → Model Garden → busque 'Claude' → Enable nos modelos"
  echo "  (sonnet, haiku, opus). O Google exige aceite de ToS por projeto via"
  echo "  Console — não existe API para isso."
  echo ""
  echo "Depois: Actions → Deploy → Run workflow (informe a tag, ex. v0.1.0)."
else
  echo "==> 5/5 gh CLI não disponível ou não autenticado."
  echo "    Configure manualmente no GitHub (Settings > Secrets and variables >"
  echo "    Actions > Variables):"
  echo ""
  echo "  GCP_WIF_PROVIDER = ${WIF_PROVIDER}"
  echo "  GCP_DEPLOYER_SA  = ${SA_EMAIL}"
  echo "  TF_STATE_BUCKET  = ${STATE_BUCKET}"
  echo ""
  echo "  Dica: instale o gh CLI (https://cli.github.com) e rode este script"
  echo "  novamente — ele configura as variáveis automaticamente."
fi

cat <<'EOF'

Único passo que NUNCA pode ser automatizado:
  Vertex AI → Model Garden → busque "Claude" → Enable (sonnet / haiku / opus).
  O Google exige aceite de ToS de parceiro por projeto via Console. Sem isso
  as chamadas à Vertex retornam 403 model not found.

AVISO: a SA de deploy é poderosa (inclui projectIamAdmin). A WIF restringe o
uso dela a workflows da branch main deste repositório — não afrouxe a
attribute-condition.
EOF
