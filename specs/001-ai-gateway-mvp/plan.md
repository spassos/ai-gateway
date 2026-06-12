# Plan 001 — Arquitetura e decisões técnicas

Implementa o [spec.md](./spec.md). Tarefas em [tasks.md](./tasks.md).

## Arquitetura

```
Máquina do desenvolvedor                 GCP (projeto central)
┌──────────────────┐                    ┌──────────────────────────────┐
│ ai-gw CLI (py)   │─ gcloud ID token ─▶│ [IAM run.invoker: grupo devs] │
│                  │◀─ virtual key ─────│ broker (FastAPI, Cloud Run)   │
│                  │                    │  - revalida token (hd=domínio)│
│ Claude Code      │                    │  - /user/new + /key/generate  │
│ Codex CLI        │── tráfego LLM ────▶│    via API admin do LiteLLM   │
│ Cursor           │   (virtual key)    │  - eventos de auditoria (PG)  │
└──────────────────┘                    │ litellm proxy (Cloud Run)     │
                                        │  - /v1/messages (Claude Code) │
                                        │  - /v1/chat/completions       │
                                        │  - budgets + SpendLogs        │
                                        │  - SA/ADC → Vertex AI         │
                                        │ Cloud SQL Postgres (compart.) │
                                        └──────────────────────────────┘
```

Dois serviços Cloud Run, um banco. O broker é o único componente com o
`LITELLM_MASTER_KEY`. A autenticação na Vertex usa a service account do Cloud
Run (`roles/aiplatform.user`) via ADC.

## Componentes

### gateway/ — LiteLLM Proxy
- Imagem oficial `ghcr.io/berriai/litellm` (tag pinada) + `config.yaml`.
- `model_list`: aliases públicos agnósticos de provedor → backends
  `vertex_ai/*`. Inclui os IDs que o Claude Code envia por padrão (sonnet/haiku
  default) para resolverem sem configuração extra do usuário.
- Modelo `mock-gpt` (`mock_response`) para e2e local sem GCP.
- `general_settings`: `master_key` e `database_url` via env.

### broker/ — FastAPI (privilegiado)
- `POST /v1/provision` (Bearer = Google ID token):
  1. Valida token: assinatura via JWKS do Google, `iss`, `exp`,
     `email_verified`, `hd == BROKER_ALLOWED_DOMAIN`.
  2. Upsert usuário LiteLLM (`/user/new`, fallback `/user/update`) com
     `max_budget=50`, `budget_duration=30d` — policy reaplicada a cada login.
  3. Rotação: lista keys do usuário (`/user/info`), deleta (`/key/delete`),
     gera nova (`/key/generate`, `key_alias=ai-gw:{email}`).
  4. Grava `audit_events`, retorna `{api_key, base_url, budget}`.
- `GET /v1/me` (Bearer = virtual key): proxy para `/key/info` + `/user/info` do
  LiteLLM — alimenta `ai-gw status` sem o CLI reter o token Google.
- `GET /healthz`.
- Dev mode: `BROKER_DEV_FAKE_AUTH=1` aceita header `X-Dev-Email` (somente
  local; recusado se a env não estiver setada).

### cli/ — pacote `ai-gw` (Typer)
- `login` — `gcloud auth print-identity-token` → broker `/v1/provision` →
  salva `~/.config/ai-gw/credentials.json` (0600). `--dev-email` para ambiente
  local.
- `connect claude-code|codex|cursor` — escreve a config do cliente (backup +
  merge não destrutivo).
- `models` — `GET {gateway}/v1/models` com a virtual key.
- `status` — broker `/v1/me` → gasto/limite/reset.
- `logout` — remove credenciais locais (revogação remota: tarefa T-22).

## Decisões e trade-offs

| Decisão | Alternativa rejeitada | Razão |
|---|---|---|
| LiteLLM OSS como motor | Proxy custom; Bifrost/Portkey | Budgets, virtual keys, spend logs e `/v1/messages` prontos no tier MIT |
| Broker próprio p/ identidade | SSO enterprise do LiteLLM | Evita licença paga; broker tem <500 LoC |
| Auth via gcloud + IAM invoker | OAuth loopback próprio | CLI trivial; autorização vira IAM (grupo Google), revogação central. ID token do gcloud sozinho seria brecha — IAM é obrigatório |
| Rotação de key a cada login | Key estável por usuário | Recuperação self-service de vazamento; gasto é por usuário, não zera |
| Budget nativo LiteLLM (`budget_duration=30d`, excedeu → HTTP 429 `budget_exceeded`) | Cron próprio de enforcement | Simplicidade no MVP; data de reset exata varia por versão (T-20) |
| Postgres único, schema `broker` separado | Banco dedicado p/ auditoria | Menos infra; sem colisão com migrações do LiteLLM |

## Modelo de dados

- Tabelas do LiteLLM (gerenciadas por ele): `LiteLLM_UserTable`,
  `LiteLLM_VerificationToken`, `LiteLLM_SpendLogs`.
- Tabela do broker (schema `broker`):

```sql
CREATE TABLE broker.audit_events (
  id          BIGSERIAL PRIMARY KEY,
  ts          TIMESTAMPTZ NOT NULL DEFAULT now(),
  actor_email TEXT NOT NULL,
  action      TEXT NOT NULL,  -- login|user_created|key_rotated|key_revoked|provision_denied
  details     JSONB NOT NULL DEFAULT '{}',
  source_ip   TEXT
);
```

## Integração por cliente

| Cliente | Mecanismo | Observações |
|---|---|---|
| Claude Code | `~/.claude/settings.json` → `env.ANTHROPIC_BASE_URL` + `env.ANTHROPIC_AUTH_TOKEN` (+ `CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1`) | usa `/v1/messages` do gateway |
| Codex CLI | `~/.codex/config.toml` → `[model_providers.ai-gw]` `base_url`, `env_key="AI_GW_API_KEY"`, `wire_api="chat"` | key só via env var; CLI grava `~/.config/ai-gw/env.sh` |
| Cursor | manual guiado: Settings → Models → Override OpenAI Base URL | **só chat/composer**; Tab/Agent ficam no backend da Cursor (não auditados) |

## Deploy (GCP)

- 2 serviços Cloud Run: `ai-gateway` (LiteLLM, público com auth por virtual
  key) e `ai-gateway-broker` (`--no-allow-unauthenticated`, invoker = grupo).
- Cloud SQL Postgres (private IP ou connector), Secret Manager para
  `LITELLM_MASTER_KEY`.
- SA do gateway: `roles/aiplatform.user`. SA do broker: acesso ao secret.
- Request timeout do Cloud Run ≥ 3600s (sessões de agente com streaming).
- Terraform em `infra/terraform/` (esqueleto no MVP, aplicável em T-17).

## Verificação

Roteiro e2e local completo no [README](../../README.md#desenvolvimento-local) e
nos critérios de aceite de cada task em [tasks.md](./tasks.md).
