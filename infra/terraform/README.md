# Deploy na GCP (T-18 / T-28)

Há dois caminhos: **pelo GitHub Actions** (recomendado, seção "Deploy pelo CI")
ou manual (seções 2–4). Em ambos, o passo 1 (Model Garden) é manual e único.

Pré-requisitos: `gcloud` autenticado como dono do projeto, `terraform >= 1.7`,
billing ativo no projeto.

## Deploy pelo CI (recomendado)

Uma vez só, na sua máquina (cria o que o CI não pode criar para si: bucket de
state, SA de deploy e a federação OIDC GitHub→GCP, restrita à branch main
deste repo — sem chave JSON em secret):

```bash
bash infra/bootstrap.sh
```

O script imprime três valores; cadastre-os em GitHub → Settings → Secrets and
variables → Actions → **Variables**: `GCP_WIF_PROVIDER`, `GCP_DEPLOYER_SA`,
`TF_STATE_BUCKET`. Recomendado: em Settings → Environments → `production`,
exija sua aprovação (required reviewers).

Depois, cada deploy é: **Actions → Deploy → Run workflow** com a tag da imagem
(ex. `v0.1.0`). O workflow builda/pusha as imagens, roda `terraform apply` com
`prod.tfvars` (allowlist de usuários versionada — mudar usuário = PR) e executa
o smoke (gateway vivo + broker negando request sem token).

## Deploy manual (alternativa)

## 1. Habilitar os modelos Claude no Model Garden (manual, uma vez)

Console → Vertex AI → Model Garden → busque "Claude" → **Enable** nos modelos
usados em `gateway/config.yaml` (sonnet/opus/haiku). Modelos parceiros exigem
aceite explícito por projeto. Gemini não precisa de aceite.

## 2. Build e push das imagens

```bash
gcloud auth login && gcloud config set project igneous-primacy-488819-g4
make push-images TAG=v0.1.0   # usa Cloud Build; cria o repo na 1ª vez via terraform
```

> Ordem na primeira vez: rode `terraform apply` uma vez só com
> `-target=google_artifact_registry_repository.images` para criar o registry,
> depois `make push-images`, depois o apply completo (o Cloud Run precisa que
> as imagens existam).

## 3. Aplicar

```bash
bash infra/bootstrap.sh              # se ainda não rodou (bucket de state)
cd infra/terraform
cp example.tfvars terraform.tfvars   # ajuste os e-mails da allowlist
terraform init -backend-config="bucket=igneous-primacy-488819-g4-tfstate"
terraform apply -target=google_artifact_registry_repository.images
cd ../.. && make push-images TAG=v0.1.0 && cd infra/terraform
terraform apply
```

Outputs: `gateway_url` (vai nos clientes) e `broker_url` (vai no CLI).

## 4. Smoke de produção

```bash
BROKER_URL=$(terraform output -raw broker_url)

# 4.1 SEM token → 403 do próprio GCP (IAM barrando, como deve ser)
curl -s -o /dev/null -w '%{http_code}\n' -X POST $BROKER_URL/v1/provision   # 403

# 4.2 Com conta da allowlist → 200 + virtual key
curl -s -X POST $BROKER_URL/v1/provision \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)"

# 4.3 CLI de verdade
AI_GW_BROKER_URL=$BROKER_URL ai-gw login
ai-gw connect claude-code && ai-gw models
```

Confirme também o caso negativo com uma conta FORA da allowlist (deve dar 403
no passo 4.2) — é o teste de que a brecha do gcloud está fechada.

## Operação

- **Adicionar/remover usuário:** edite `gateway_users` no tfvars e
  `terraform apply` (atualiza o IAM e a allowlist do broker juntos).
- **Nova versão:** `make push-images TAG=v0.2.0`, mude `image_tag`, apply.
- **Custo por usuário:** SQL em `LiteLLM_SpendLogs` (Cloud SQL) ou painel do
  LiteLLM em `<gateway_url>/ui` (login com a master key).
- O tfstate (no bucket GCS, com versioning) contém segredos — mantenha o
  acesso ao bucket restrito a você e à SA de deploy.
