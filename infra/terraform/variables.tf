variable "project_id" {
  description = "Projeto GCP transversal que centraliza o billing dos modelos"
  type        = string
}

variable "region" {
  description = "Região dos serviços Cloud Run / Cloud SQL / Artifact Registry"
  type        = string
  default     = "us-central1"
}

variable "vertex_location" {
  description = <<-EOT
    Região dos modelos no Vertex AI. Atenção: os modelos Claude (parceiros)
    não estão em todas as regiões — us-east5 e global são as opções usuais;
    confira a disponibilidade no Model Garden antes de mudar.
  EOT
  type        = string
  default     = "us-east5"
}

variable "allowed_domain" {
  description = "Domínio Google Workspace aceito pelo broker (claim hd). Vazio se não houver Workspace."
  type        = string
  default     = ""
}

variable "gateway_users" {
  description = <<-EOT
    E-mails Google autorizados a usar o gateway (sem Workspace usamos
    allowlist). Cada e-mail recebe roles/run.invoker no broker (autorização
    primária) e entra no BROKER_ALLOWED_EMAILS (defesa em profundidade).
  EOT
  type        = list(string)
}

variable "user_max_budget" {
  description = "Budget por usuário em USD"
  type        = number
  default     = 50
}

variable "image_tag" {
  description = "Tag das imagens no Artifact Registry (nunca usar latest em produção)"
  type        = string
}
