PYTHON ?= python3.11
PROJECT ?= example-project

.PHONY: setup project-pages docs-dev docs-build llms index reindex index-all watch watch-all hub-dev hub-status hub-install hub-start hub-stop hub-restart hub-uninstall hub-launchd-status hub-logs hub-menu-build hub-menu-start hub-menu-stop hub-menu-restart hub-menu-status mcp-dev mcp-test codebase-memory-install codebase-memory-status codebase-memory-index healthcheck rag-health check-secrets lint scaffold-docs scaffold-docs-write logs clean-cache validate-configs

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

hub-dev:
	$(PYTHON) scripts/hub-dev

hub-status:
	$(PYTHON) scripts/hub-status

hub-install:
	$(PYTHON) scripts/hub-launchd install

hub-start:
	$(PYTHON) scripts/hub-launchd start

hub-stop:
	$(PYTHON) scripts/hub-launchd stop

hub-restart:
	$(PYTHON) scripts/hub-launchd restart

hub-uninstall:
	$(PYTHON) scripts/hub-launchd uninstall

hub-launchd-status:
	$(PYTHON) scripts/hub-launchd status

hub-logs:
	$(PYTHON) scripts/hub-launchd logs

hub-menu-build:
	$(PYTHON) scripts/hub-menubar build

hub-menu-start:
	$(PYTHON) scripts/hub-menubar start

hub-menu-stop:
	$(PYTHON) scripts/hub-menubar stop

hub-menu-restart:
	$(PYTHON) scripts/hub-menubar restart

hub-menu-status:
	$(PYTHON) scripts/hub-menubar status

mcp-dev:
	$(PYTHON) mcp/server.py

mcp-test:
	$(PYTHON) scripts/mcp-test

codebase-memory-install:
	mkdir -p storage/runtime/bin
	curl -fsSL https://raw.githubusercontent.com/DeusData/codebase-memory-mcp/main/install.sh | bash -s -- --standard --dir="$(CURDIR)/storage/runtime/bin" --skip-config

codebase-memory-status:
	$(PYTHON) scripts/codebase-memory status --project "$(PROJECT)"

codebase-memory-index:
	$(PYTHON) scripts/codebase-memory index --project "$(PROJECT)" --mode moderate

healthcheck:
	$(PYTHON) scripts/healthcheck

rag-health: healthcheck

check-secrets:
	$(PYTHON) scripts/check-secrets-before-index --project "$(PROJECT)"

validate-configs:
	$(PYTHON) scripts/validate-configs

lint:
	$(PYTHON) scripts/lint-project --project "$(PROJECT)"

scaffold-docs:
	$(PYTHON) scripts/scaffold-project-docs --project "$(PROJECT)"

scaffold-docs-write:
	$(PYTHON) scripts/scaffold-project-docs --project "$(PROJECT)" --write

logs:
	$(PYTHON) scripts/read-logs --project "$(PROJECT)"

clean-cache:
	rm -rf docs-site/dist .npm-cache storage/generated/*
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
