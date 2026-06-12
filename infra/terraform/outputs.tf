output "gateway_url" {
  description = "URL pública do LiteLLM — é o base_url que o CLI entrega aos clientes"
  value       = google_cloud_run_v2_service.gateway.uri
}

output "broker_url" {
  description = "URL do broker — use em `ai-gw login --broker-url ...` ou AI_GW_BROKER_URL"
  value       = google_cloud_run_v2_service.broker.uri
}

output "artifact_registry" {
  description = "Prefixo do registry para o push das imagens"
  value       = local.registry
}
