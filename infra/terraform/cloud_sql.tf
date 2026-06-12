# TODO(T-18): Cloud SQL Postgres.
#
# - google_sql_database_instance (POSTGRES_16, private IP ou Cloud SQL connector)
# - google_sql_database "litellm" (tabelas do LiteLLM + schema broker.audit_events)
# - google_sql_user com senha em Secret Manager
# - Conectar os dois serviços Cloud Run via cloudsql annotations / vpc connector
