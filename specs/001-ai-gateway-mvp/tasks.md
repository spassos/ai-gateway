# Tasks 001 — AI Gateway MVP

Ordenadas por dependência. Status: `[x]` feito · `[ ]` pendente.

## P0 — Scaffolding e ambiente local

- [x] **T-01** Docs spec-driven (`constitution.md`, `spec.md`, `plan.md`, `tasks.md`).
- [x] **T-02** Raiz do repo: `.gitignore`, `.env.example`, `Makefile`, `README.md`.
- [x] **T-03** `gateway/config.yaml` com model_list (Claude/Gemini Vertex + `mock-gpt`) e `gateway/Dockerfile`.
      _Aceite:_ litellm sobe com a config e responde `/health/liveliness`.
- [x] **T-04** `docker-compose.yml` (postgres:16 + litellm + broker).
      _Aceite:_ `make up` deixa os três serviços saudáveis; LiteLLM migra o banco.

## P1 — Broker

- [x] **T-05** Pacote `broker/`: config (pydantic-settings), app factory, `/healthz`.
- [x] **T-06** `auth.py`: validação do Google ID token (JWKS, iss, exp, email_verified, hd) + modo dev `BROKER_DEV_FAKE_AUTH`.
- [x] **T-07** `litellm_client.py`: upsert de usuário (budget $50/30d), listagem/rotação/geração de keys via API admin.
- [x] **T-08** `audit.py`: tabela `broker.audit_events` (autocreate) + writer.
- [x] **T-09** `routes.py`: `POST /v1/provision` e `GET /v1/me`.
      _Aceite:_ `curl -X POST :8080/v1/provision -H 'X-Dev-Email: dev@empresa.com'` retorna virtual key; evento em `broker.audit_events`; completion mock via `:4000/v1/chat/completions` gera linha em `LiteLLM_SpendLogs`.
- [x] **T-10** Testes pytest do broker (LiteLLM mockado): provision feliz, domínio errado negado + auditado, rotação deleta key antiga.

## P2 — CLI

- [x] **T-11** Pacote `cli/` (`ai-gw`, Typer): `store.py` (credenciais 0600), `broker_client.py`, `gcloud_auth.py`.
- [x] **T-12** `ai-gw login` (gcloud → provision → salva credenciais; `--dev-email` p/ local).
- [x] **T-13** Connectors: `connect claude-code` (merge settings.json + backup), `connect codex` (tomlkit + env.sh), `connect cursor` (instruções guiadas + aviso de cobertura parcial).
- [x] **T-14** `ai-gw models`, `ai-gw status`, `ai-gw logout`.
- [x] **T-15** Testes dos connectors (HOME temporário): merge preserva chaves existentes, backup criado, toml válido.

## P3 — Infra e CI

- [x] **T-16** Esqueleto Terraform (`infra/terraform/`) com recursos comentados/TODO: 2× Cloud Run, Cloud SQL, IAM (incl. binding `run.invoker` → grupo de devs), Secret Manager.
- [x] **T-17** CI GitHub Actions: ruff + pytest (broker, cli) + docker build.

## P4 — Pós-MVP (não nesta sessão)

- [ ] **T-18** Terraform aplicável (substituir TODOs por recursos reais; smoke de prod confirma 403 p/ conta fora do grupo).
- [ ] **T-19** Alertas de budget (Slack webhook a 80%).
- [ ] **T-20** Alinhamento de budget ao mês-calendário (`budget_reset_at` via cron).
- [ ] **T-21** `ai-gw login --no-rotate` (reuso de key p/ segunda máquina).
- [ ] **T-22** Revogação remota de key no `ai-gw logout`.
- [ ] **T-23** Export/reconciliação BigQuery (labels `user_id` nas chamadas Vertex).
- [ ] **T-24** Script de relatório admin (gasto por usuário/modelo/mês).
- [ ] **T-25** Storage de credenciais em keyring do SO.
- [ ] **T-26** (Opcional) Modelos extras: Qwen/gpt-oss via Model Garden (só model_list); OpenAI proprietário (`openai/*`, exige API key e billing separado); Ollama self-hosted (`api_base`).
- [ ] **T-27** Validar Claude Code real contra o gateway (aliases de modelo default resolvem sem config extra).
