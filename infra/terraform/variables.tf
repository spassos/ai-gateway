variable "project_id" {
  description = "Projeto GCP transversal que centraliza o billing dos modelos"
  type        = string
}

variable "region" {
  description = "Região dos serviços Cloud Run / Cloud SQL"
  type        = string
  default     = "us-east5"
}

variable "vertex_location" {
  description = "Região dos modelos no Vertex AI"
  type        = string
  default     = "us-east5"
}

variable "allowed_domain" {
  description = "Domínio Google Workspace aceito pelo broker (claim hd)"
  type        = string
}

variable "dev_group" {
  description = "Grupo Google com acesso ao gateway (recebe roles/run.invoker no broker)"
  type        = string
  # ex.: "group:ai-gateway-users@empresa.com"
}

variable "user_max_budget" {
  description = "Budget por usuário em USD"
  type        = number
  default     = 50
}
