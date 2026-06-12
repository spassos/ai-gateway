.PHONY: up down logs test lint smoke install-dev push-images

# Projeto/região do deploy (ver infra/terraform/example.tfvars)
GCP_PROJECT ?= igneous-primacy-488819-g4
GCP_REGION  ?= us-central1
REGISTRY     = $(GCP_REGION)-docker.pkg.dev/$(GCP_PROJECT)/ai-gateway

push-images: ## Build + push via Cloud Build. Uso: make push-images TAG=v0.1.0
ifndef TAG
	$(error Defina a tag: make push-images TAG=v0.1.0)
endif
	gcloud builds submit gateway --project $(GCP_PROJECT) --tag $(REGISTRY)/gateway:$(TAG)
	gcloud builds submit broker --project $(GCP_PROJECT) --tag $(REGISTRY)/broker:$(TAG)

up: ## Sobe o stack local (postgres + litellm + broker)
	docker compose up --build -d
	docker compose ps

down:
	docker compose down

logs:
	docker compose logs -f

install-dev: ## Instala broker e cli em modo dev (use dentro de um venv)
	pip install -e "./broker[dev]" -e "./cli[dev]"

lint:
	ruff check broker cli
	ruff format --check broker cli

test:
	cd broker && python -m pytest -q
	cd cli && python -m pytest -q

smoke: ## E2E local: provisiona key, chama o modelo mock, confere status
	@set -e; \
	echo "1/4 broker healthz..."; \
	curl -fsS --retry 12 --retry-delay 5 --retry-all-errors localhost:8080/healthz > /dev/null; \
	echo "2/4 litellm liveliness..."; \
	curl -fsS localhost:4000/health/liveliness > /dev/null; \
	echo "3/4 provisionando key para dev@empresa.com..."; \
	KEY=$$(curl -fsS -X POST localhost:8080/v1/provision -H 'X-Dev-Email: dev@empresa.com' | python3 -c 'import sys,json; print(json.load(sys.stdin)["api_key"])'); \
	echo "4/4 completion no modelo mock..."; \
	curl -fsS localhost:4000/v1/chat/completions \
	  -H "Authorization: Bearer $$KEY" -H 'Content-Type: application/json' \
	  -d '{"model":"mock-gpt","messages":[{"role":"user","content":"ping"}]}' > /dev/null; \
	echo "smoke OK"
