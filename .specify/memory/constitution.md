# Constituição do Projeto — AI Gateway

Princípios que governam todas as decisões técnicas deste repositório. Mudanças
neste documento exigem revisão do time de plataforma.

## Princípio 1 — Reusar antes de construir

O LiteLLM Proxy (OSS/MIT) é o motor do gateway. Não escrevemos lógica de proxy,
roteamento de modelos, cálculo de custo ou enforcement de budget — isso é do
LiteLLM. Nosso código se limita a **cola**: o broker de identidade e o CLI de
conexão.

## Princípio 2 — Permanecer no tier gratuito do LiteLLM

Nenhum componente pode depender de recursos enterprise do LiteLLM (SSO nativo,
audit logs estruturados, RBAC avançado). O que for indispensável (auditoria de
identidade, login corporativo) é replicado minimamente no broker.

## Princípio 3 — Nenhum segredo de longa duração na máquina do desenvolvedor

O único segredo que chega ao desenvolvedor é a **virtual key pessoal** dele
(rotacionável a cada login). O `LITELLM_MASTER_KEY` vive apenas no Secret
Manager e no ambiente do broker. Credenciais de Vertex AI são a service account
do Cloud Run via ADC — nunca arquivos JSON distribuídos.

## Princípio 4 — Toda ação que muda estado gera evento de auditoria

Qualquer ação do broker que cria/rotaciona/revoga usuário ou key grava uma
linha em `audit_events` antes de responder. Uso de modelo é auditado pelo
LiteLLM em `LiteLLM_SpendLogs`. Sem exceções.

## Princípio 5 — Autorização é do IAM, autenticação é do Google

O acesso ao broker é controlado por IAM do GCP (`roles/run.invoker` em grupo
dedicado), nunca por listas de e-mail hardcoded. O broker valida identidade
(assinatura JWKS, `exp`, `email_verified`, `hd`) como defesa em profundidade,
não como mecanismo primário de autorização.

## Princípio 6 — Spec-driven

Toda feature nasce de um spec em `specs/NNN-nome/` (spec.md → plan.md →
tasks.md) antes do código. PRs referenciam a task que implementam.

## Restrições técnicas

- Python ≥ 3.12 em broker e CLI; `ruff` para lint/format; `pytest` para testes.
- Infra declarada em Terraform (`infra/terraform/`).
- Deploy: Cloud Run + Cloud SQL Postgres. Imagens pinadas por tag (nunca
  `latest` em produção).
- Ambiente local de desenvolvimento 100% funcional via `docker compose up`,
  sem credenciais GCP (modelo mock).
