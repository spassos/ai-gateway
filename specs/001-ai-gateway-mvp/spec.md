# Spec 001 — AI Gateway MVP

**Status:** aprovado · **Owner:** plataforma · **Criado:** 2026-06-12

## Problema

Desenvolvedores usam Claude Code, Codex CLI e Cursor com tokens/contas pessoais
de LLM. Não há visibilidade de custo, não há auditoria e o gasto não é
centralizado no projeto transversal da empresa na GCP.

## Objetivo

Um gateway central na GCP pelo qual os clientes de codificação acessam os
modelos do Vertex AI (Claude, Gemini), com auditoria por usuário, limite de
US$ 50/usuário e onboarding via um único comando de CLI.

## User stories

- **US-1** — Como desenvolvedor, rodo `ai-gw login` autenticado com minha conta
  Google corporativa (via gcloud) e recebo acesso ao gateway sem manipular
  chaves de API manualmente.
- **US-2** — Como desenvolvedor, rodo `ai-gw connect claude-code` e em menos de
  1 minuto o Claude Code passa a funcionar através do gateway.
- **US-3** — Como dono da plataforma, consigo ver quem gastou o quê, em qual
  modelo e quando (consulta SQL sobre os spend logs).
- **US-4** — Como dono da plataforma, quando um usuário atinge US$ 50 no
  período, as requisições dele são bloqueadas com erro claro até o reset da
  janela.
- **US-5** — Como desenvolvedor, rodo `ai-gw status` e vejo meu gasto atual,
  meu limite e a data de reset; `ai-gw models` lista os modelos disponíveis.

## Requisitos funcionais

| ID | Requisito |
|----|-----------|
| FR-1 | Gateway expõe endpoint OpenAI-compatible (`/v1/chat/completions`, `/v1/models`) para Codex e Cursor. |
| FR-2 | Gateway expõe endpoint Anthropic (`/v1/messages`) para Claude Code. |
| FR-3 | Login restrito a contas Google do domínio corporativo; autorização primária via IAM (`roles/run.invoker` no grupo de devs). |
| FR-4 | Provisionamento de key idempotente, vinculado ao e-mail; re-login rotaciona a key sem zerar o gasto. |
| FR-5 | Cada usuário tem `max_budget = 50 USD` e `budget_duration = 30d`; ao exceder, o gateway retorna HTTP 429 `budget_exceeded` (verificado no LiteLLM 1.88: `"ExceededBudget: User=... over budget"`). |
| FR-6 | `ai-gw status` mostra gasto / limite / reset; `ai-gw models` lista modelos via `GET /v1/models`. |
| FR-7 | Toda emissão/rotação/revogação de key e tentativa negada gera evento em `audit_events`; todo request a modelo gera linha em `LiteLLM_SpendLogs`. |
| FR-8 | Connectors do CLI para Claude Code (settings.json), Codex (config.toml) e Cursor (instruções guiadas). |

## Requisitos não funcionais

- **NFR-1** — Streaming (SSE) suportado fim a fim para todos os clientes.
- **NFR-2** — Erro de budget excedido é determinístico e parseável pelo CLI.
- **NFR-3** — Broker stateless (compatível com scale-to-zero no Cloud Run).
- **NFR-4** — Nenhum PII além de e-mail corporativo + dados de gasto.
- **NFR-5** — Paridade dev local: `docker compose up` sobe o stack completo com
  modelo mock, sem credenciais GCP.
- **NFR-6** — O token do Google nunca é logado nem persistido pelo broker.

## Fora de escopo (MVP)

- Reconciliação com billing export do BigQuery.
- UI web de administração (o painel do LiteLLM existe, mas não é requisito).
- Budgets por time/projeto (apenas por usuário).
- Políticas de expiração de key.
- Roteamento de Tab/autocomplete do Cursor (limitação do produto Cursor: apenas
  chat/composer aceitam endpoint customizado — **documentar com destaque**).
- Modelos fora do Vertex AI (OpenAI proprietário, Ollama self-hosted) — ficam
  como extensões opcionais em tasks.md.

## Desvios conhecidos e aceitos

- A janela de reset do budget é controlada pelo LiteLLM (`budget_duration=30d`).
  No LiteLLM 1.88 o `budget_reset_at` observado alinhou ao início do mês
  seguinte (2026-07-01); o comportamento varia entre versões — confirmar na
  versão pinada e alinhar ao mês-calendário se necessário (T-20).
- **Modelos de custo zero pulam os checks de budget** no LiteLLM
  (`_is_model_cost_zero`). Por isso o modelo `mock-gpt` local tem custo
  sintético no config. Os SpendLogs do mock registram $0 (short-circuit do
  `mock_response`) — para simular gasto em dev, use `/user/update` na API admin.
- Rotação de key a cada login invalida a config de uma segunda máquina do mesmo
  usuário. Mitigação futura: `ai-gw login --no-rotate` (T-21).

## Métricas de sucesso

- Onboarding (login + connect) em < 2 minutos.
- 100% das requisições a modelos atribuíveis a um e-mail.
- 0 chaves de provedor (Vertex/Anthropic) distribuídas a desenvolvedores.
