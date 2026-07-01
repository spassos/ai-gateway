resource "google_sql_database_instance" "main" {
  name             = "ai-gateway-pg"
  database_version = "POSTGRES_16"
  region           = var.region

  settings {
    # Edição ENTERPRISE (não ENTERPRISE_PLUS): só ela aceita os tiers
    # shared-core baratos (db-f1-micro). Sem isto, a API assume ENTERPRISE_PLUS
    # e rejeita o db-f1-micro.
    edition = "ENTERPRISE"
    # Menor tier; subir para db-custom-1-3840+ quando houver uso real.
    tier = "db-f1-micro"
    # ALWAYS = ligado 24/7; NEVER = parado (paga só o disco). Sem usuários,
    # setar db_activation_policy=NEVER zera quase todo o custo sem destruir o
    # banco — religa em ~1 min quando for testar.
    activation_policy = var.db_activation_policy
    # Disco mínimo e sem autoresize: o volume de dados (keys, spend, audit) é
    # ínfimo; não deixamos o disco crescer (e encarecer) sozinho.
    disk_size         = 10
    disk_autoresize   = false
    ip_configuration {
      # Sem IP público exposto a redes: o acesso é só via Cloud SQL connector
      # (volume /cloudsql nos serviços Cloud Run).
      ipv4_enabled = true
      ssl_mode     = "ENCRYPTED_ONLY"
    }
    backup_configuration {
      # Backup desligado no ambiente de testes (sem usuários = sem dado a
      # proteger). Reativar antes de ir a produção.
      enabled = false
    }
  }

  # Proteção contra `terraform destroy` acidental do banco de auditoria.
  deletion_protection = true
  depends_on          = [google_project_service.apis]
}

resource "google_sql_database" "litellm" {
  name     = "litellm"
  instance = google_sql_database_instance.main.name
}

resource "random_password" "db" {
  length  = 32
  special = false
}

resource "google_sql_user" "litellm" {
  name     = "litellm"
  instance = google_sql_database_instance.main.name
  password = random_password.db.result
}

locals {
  # Forma unix-socket do Cloud SQL connector; funciona para o Prisma (LiteLLM)
  # e para o SQLAlchemy/psycopg (broker, que troca o scheme em runtime).
  database_url = format(
    "postgresql://%s:%s@localhost/%s?host=/cloudsql/%s",
    google_sql_user.litellm.name,
    random_password.db.result,
    google_sql_database.litellm.name,
    google_sql_database_instance.main.connection_name,
  )
}
