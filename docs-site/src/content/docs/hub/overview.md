---
title: Overview
description: What the local AI Docs Hub owns and what it does not own.
---

AI Docs Hub - локальный coordination layer для нескольких проектов. Он помогает агентам и человеку находить проектную документацию, но не должен превращаться в ручную копию каждой базы знаний.

## Ownership

Проектная документация хранится в проекте:

- `AGENTS.md`;
- `README.md`;
- `docs/architecture/`;
- `docs/modules/`;
- `docs/decisions/`;
- `docs/api/`;
- `docs/deployment/`;
- `docs/operations/`;
- `docs/infrastructure/`;
- `docs/configuration.md`;
- `docs/security.md`;
- `docs/data.md`;
- `docs/integrations.md`;
- `docs/observability.md`;
- `docs/testing.md`;
- `docs/troubleshooting.md`;
- `docs/development.md`;
- `docs/glossary.md`.

Хаб хранит инфраструктуру:

- project connection configs;
- local indexes and generated files;
- MCP bridge;
- docs-site;
- shared templates;
- shared agent policies.

## Source Of Truth

- Документация хаба: `docs/`.
- Страницы сайта: `docs-site/src/content/docs/`.
- Документация проектов: сами подключенные проекты.
- RAG indexes, generated project pages и `llms*.txt`: derived artifacts.

Когда меняется архитектура, runtime, RAG, MCP, docs-site, indexing, generated context, project config behavior или agent workflow, нужно обновить `docs/`, соответствующую страницу docs-site и change note в `docs/changes/`, если изменение влияет на использование, эксплуатацию, отладку или расширение.

## Local-First

Штатная реализация не отправляет проектные файлы во внешние API, не использует облачные vector DB и не меняет подключенные проекты без явного действия пользователя.

Local stack:

- Python 3.11 для scripts, Lite RAG, MCP, healthcheck, watcher, scaffold и генераторов.
- Node.js 22/npm 10 для Astro Starlight docs-site.
- Local filesystem storage в `storage/`.
- Optional macOS `launchd` для persistent runtime.

## Основные Workflows

- `make hub-dev` - поднять docs-site и watcher в foreground.
- `make hub-status` - проверить live runtime, docs-site, RAG, MCP, generated artifacts и watcher heartbeat.
- `make index PROJECT=...` - построить локальный RAG index проекта.
- `make llms` - обновить generated LLM context.
- `make scaffold-docs PROJECT=...` - показать, какие проектные docs можно создать.
- `make mcp-test` - проверить stdio MCP bridge.
