#!/usr/bin/env bash
# Bootstrap único do deploy via GitHub Actions (rodar UMA vez, como dono do
# projeto). Cria o que o CI não pode criar para si mesmo:
#   1. bucket GCS para o state do Terraform
#   2. service account de deploy (poderosa — ver aviso no fim)
#   3. Workload Identity Federation restrita a este repositório
# Depois, configure as repo variables no GitHub (instruções no fim da saída).
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

# Papéis que o terraform apply + cloud build precisam. projectIamAdmin é o
# mais sensível (gerencia bindings) — por isso a WIF abaixo restringe o uso
# desta SA à branch main DESTE repositório.
for role in \
  roles/run.admin \
  roles/cloudsql.admin \
  roles/secretmanager.admin \
  roles/artifactregistry.admin \
  roles/cloudbuild.builds.editor \
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

cat <<EOF

Bootstrap concluído. Configure no GitHub (Settings > Secrets and variables >
Actions > Variables):

  GCP_WIF_PROVIDER = ${WIF_PROVIDER}
  GCP_DEPLOYER_SA  = ${SA_EMAIL}
  TF_STATE_BUCKET  = ${STATE_BUCKET}

Recomendado: Settings > Environments > production > required reviewers (você),
para o deploy exigir um clique de aprovação.

AVISO: a SA de deploy é poderosa (inclui projectIamAdmin). A WIF restringe o
uso dela a workflows da branch main de ${GITHUB_REPO} — não afrouxe a
attribute-condition.
EOF
