PYTHON ?= python3.11
PROJECT ?= example-project

.PHONY: setup project-pages docs-dev docs-build llms index reindex index-all watch watch-all mcp-dev mcp-test healthcheck rag-health check-secrets lint logs clean-cache validate-configs

setup:
	$(PYTHON) -m venv .venv
	./scripts/docs-npm install
	$(PYTHON) scripts/generate-project-pages
	$(PYTHON) scripts/validate-configs

project-pages:
	$(PYTHON) scripts/generate-project-pages

docs-dev: project-pages
	./scripts/docs-npm run dev -- --host 0.0.0.0

docs-build: project-pages
	./scripts/docs-npm run build

llms: project-pages
	$(PYTHON) scripts/generate-llms

index:
	$(PYTHON) scripts/index-project --project "$(PROJECT)"

reindex:
	$(PYTHON) scripts/index-project --project "$(PROJECT)" --reindex

index-all:
	$(PYTHON) scripts/index-project --all

watch:
	$(PYTHON) scripts/watch-project --project "$(PROJECT)"

watch-all:
	$(PYTHON) scripts/watch-project --all

mcp-dev:
	$(PYTHON) mcp/server.py

mcp-test:
	$(PYTHON) scripts/mcp-test

healthcheck:
	$(PYTHON) scripts/healthcheck

rag-health: healthcheck

check-secrets:
	$(PYTHON) scripts/check-secrets-before-index --project "$(PROJECT)"

validate-configs:
	$(PYTHON) scripts/validate-configs

lint:
	$(PYTHON) scripts/lint-project --project "$(PROJECT)"

logs:
	$(PYTHON) scripts/read-logs --project "$(PROJECT)"

clean-cache:
	rm -rf docs-site/dist .npm-cache storage/generated/*
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
