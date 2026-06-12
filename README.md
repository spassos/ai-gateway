# AI Gateway

Gateway corporativo de LLMs: Claude Code, Codex CLI e Cursor acessam os modelos
do **Vertex AI** (Claude, Gemini) através de um projeto transversal na GCP —
sem tokens pessoais, com **auditoria por usuário** e **limite de US$ 50/usuário**.

```
Máquina do desenvolvedor                 GCP (projeto central)
┌──────────────────┐                    ┌──────────────────────────────┐
│ ai-gw CLI        │─ gcloud ID token ─▶│ [IAM run.invoker: grupo devs] │
│                  │◀─ virtual key ─────│ broker (FastAPI, Cloud Run)   │
│ Claude Code      │                    │ litellm proxy (Cloud Run)     │
│ Codex CLI        │── tráfego LLM ────▶│   budgets + spend logs        │
│ Cursor           │   (virtual key)    │   SA/ADC → Vertex AI          │
└──────────────────┘                    │ Cloud SQL Postgres            │
                                        └──────────────────────────────┘
```

- **Motor:** [LiteLLM Proxy](https://docs.litellm.ai/) (OSS) — roteamento,
  custo por request, budgets e virtual keys.
- **Broker:** FastAPI próprio — troca o Google ID token (via `gcloud`) por uma
  virtual key pessoal e grava auditoria de identidade.
- **CLI `ai-gw`:** onboarding em um comando.

Docs spec-driven: [constituição](.specify/memory/constitution.md) ·
[spec](specs/001-ai-gateway-mvp/spec.md) ·
[plan](specs/001-ai-gateway-mvp/plan.md) ·
[tasks](specs/001-ai-gateway-mvp/tasks.md)

## Uso (desenvolvedor)

```bash
pipx install ai-gw                      # ou: uv tool install ai-gw
gcloud auth login                       # conta corporativa

ai-gw login                             # provisiona sua key pessoal
ai-gw connect claude-code               # ou: codex / cursor
ai-gw models                            # modelos disponíveis
ai-gw status                            # gasto / limite / reset
```

Ao atingir US$ 50 no período de 30 dias, o gateway bloqueia novas requisições
(HTTP 429 `budget_exceeded`) até o reset. `ai-gw login` de novo **rotaciona** sua
key (não zera o gasto) — é a recuperação para key vazada.

> **Cursor:** apenas chat/composer usa o gateway. Tab/autocomplete e parte do
> Agent ficam nos servidores da Cursor (fora da auditoria e do budget).

## Desenvolvimento local

Stack completo sem credenciais GCP (modelo `mock-gpt`):

```bash
cp .env.example .env
make up        # postgres + litellm (4000) + broker (8080)
make smoke     # provisiona key + completion mock fim a fim
```

Teste manual:

```bash
# provisiona (dev mode aceita X-Dev-Email; em prod é o token do gcloud)
curl -X POST localhost:8080/v1/provision -H 'X-Dev-Email: dev@empresa.com'

# completion com a key retornada
curl localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-..." -H 'Content-Type: application/json' \
  -d '{"model":"mock-gpt","messages":[{"role":"user","content":"ping"}]}'

# auditoria
docker compose exec postgres psql -U litellm -c 'SELECT * FROM broker.audit_events;'
docker compose exec postgres psql -U litellm -c 'SELECT "user", model, spend FROM "LiteLLM_SpendLogs";'
```

CLI contra o ambiente local:

```bash
python -m venv .venv && source .venv/bin/activate
make install-dev
ai-gw login --dev-email dev@empresa.com
ai-gw connect claude-code && cat ~/.claude/settings.json
```

Testes e lint: `make test` · `make lint`

## Segurança (resumo)

1. **Autorização primária = IAM:** o broker roda sem `allUsers`; só quem tem
   `roles/run.invoker` (grupo Workspace ou, sem Workspace, e-mails individuais
   da allowlist `gateway_users` no Terraform) chega nele. Token do gcloud
   sozinho **não** dá acesso.
2. **Defesa em profundidade:** o broker revalida assinatura/`exp`/
   `email_verified` e o domínio (`BROKER_ALLOWED_DOMAIN`) **ou** a allowlist
   (`BROKER_ALLOWED_EMAILS`); nada configurado nega tudo. Token nunca é logado.
3. **Segredos:** o `LITELLM_MASTER_KEY` existe só no Secret Manager/broker. O
   dev recebe apenas a própria virtual key (rotacionável). Vertex AI é acessado
   pela service account do Cloud Run — nenhuma chave de provedor distribuída.

## Estrutura

| Diretório | Conteúdo |
|---|---|
| `gateway/` | Config + imagem do LiteLLM Proxy |
| `broker/` | Serviço FastAPI de provisionamento (privilegiado) |
| `cli/` | Pacote `ai-gw` |
| `infra/terraform/` | Infra GCP (esqueleto — T-18) |
| `specs/` | Spec-driven development (spec/plan/tasks) |
