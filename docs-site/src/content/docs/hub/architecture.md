---
title: Архитектура
description: Слои, границы и runtime-модель локального AI Docs Hub.
---

AI Docs Hub - локальный инфраструктурный репозиторий для документации, generated-контекста, Lite RAG-индексов и MCP-доступа.

Хаб намеренно разделен на независимые слои. Это сохраняет изоляцию проектной документации и делает generated-артефакты воспроизводимыми.

## Карта Стеков

- Python 3.11: operational scripts, project config loading, Lite RAG, MCP stdio server, healthcheck, status API source data, allowlisted fix actions, watcher, documentation scaffold, secret scanning, generated project pages и генерация `llms*.txt`.
- Node.js 22 LTS и npm 10: runtime и build pipeline для docs-site.
- Astro 6 и Starlight: документационный сайт, `/status/` page shell, status/fix API endpoints, навигация, search index build и rendering из `docs-site/src/content/docs/`.
- Markdown docs-as-code: source-документация хаба в `docs/`, source-страницы сайта в `docs-site/src/content/docs/` и документация подключенных проектов внутри самих проектов.
- YAML project config: `configs/projects/*.yaml` задают project root, namespace, source include/exclude rules, agent rules и docs backend mode.
- MkDocs adapter: read-only structural discovery для проектов с `mkdocs.yml` или `mkdocs.yaml`.
- Lite JSON/BM25 RAG: локальная индексация и поиск по разрешенной документации проектов, хранение в `storage/index`.
- MCP stdio bridge: `mcp/server.py` отдает project-scoped tools для Codex и других MCP clients.
- Local runtime: `scripts/hub-dev` супервизирует docs-site, watcher и local fix action server в foreground.
- macOS `launchd`: optional persistent supervisor для того же `hub-dev`.
- macOS menu bar app: optional Swift/AppKit wrapper для быстрого доступа к status/dashboard.
- Generated artifacts: `storage/generated`, `docs-site/public/llms*.txt`, `docs-site/src/content/docs/projects/*`, runtime heartbeats, logs и indexes.

Docker, RAGFlow, external vector databases, cloud search и remote LLM APIs не входят в default working stack.

## Docs-As-Code

Подключенные проекты хранят source-документацию в своих репозиториях. Хаб читает только разрешенные файлы через `configs/projects/*.yaml`.

Собственная source-документация хаба живет в `docs/`. Hand-authored страницы сайта живут в `docs-site/src/content/docs/` и должны отражать тот же смысл. Generated project pages под `docs-site/src/content/docs/projects/*` не редактируются вручную.

## Source Discovery

Project config строит effective source plan:

1. Берутся `sources`, `include` и `exclude` из YAML config.
2. Если `docs_backend: auto` и найден `mkdocs.yml` или `mkdocs.yaml`, MkDocs adapter безопасно читает структурные поля.
3. Если `docs_backend: mkdocs`, MkDocs config ожидается явно; при отсутствии хаб пишет warning и продолжает по обычным include rules.
4. Если `docs_backend: standard`, MkDocs игнорируется.
5. Перед чтением файлов применяются exclude rules, path safety и secret scan.

MkDocs adapter читает `site_name`, `docs_dir`, `site_dir`, `nav`, `exclude_docs`, `draft_docs`, `not_in_nav` и простой `INHERIT`. Он не выполняет `mkdocs build`, plugins, hooks, Python code или Markdown extensions.

## Lite RAG

RAG backend по умолчанию - локальное JSON/BM25-хранилище в `storage/index`.

Индекс project-scoped: каждый проект имеет собственный namespace и JSON-файл. Search results возвращают source path, heading/section, score, confidence, updated timestamp, content hash и snippet.

Перед индексацией хаб:

- проверяет project config;
- строит effective source plan;
- применяет include/exclude rules;
- блокирует secret-looking paths и content;
- режет Markdown на chunks;
- пишет operation log в `storage/index/{project}_log.jsonl`.

## Generated Context

`scripts/generate-llms` создает:

- `docs-site/public/llms.txt`;
- `docs-site/public/llms-full.txt`;
- `docs-site/public/llms-small.txt`;
- mirrored copies в `storage/generated/`;
- `storage/generated/llms-report.json`.

Эти файлы являются derived artifacts и не редактируются вручную.

## MCP Bridge

`mcp/server.py` - stdio MCP server. Он предоставляет tools для списка проектов, профилей, поиска, чтения разрешенных документов, индексации, lint, scaffold, healthcheck и operation logs.

MCP работает через stdout/stdin JSON-RPC. Stdout зарезервирован для protocol messages; logs должны идти в stderr.

Project-scoped запуск:

```sh
python3.11 mcp/server.py --project example-project
```

В этом режиме tool calls не могут переключиться на другой project.

## Runtime

Штатный локальный runtime:

- `make docs-dev` - только docs-site.
- `make watch` или `make watch-all` - foreground watcher.
- `make hub-dev` - docs-site и watcher вместе, с heartbeat в `storage/runtime/hub-dev.status.json`.
- `make hub-install && make hub-start` - persistent macOS `launchd` запуск того же `hub-dev`.

Live status проверяется командой:

```sh
make hub-status
```

GUI dashboard доступен на:

```text
http://localhost:4321/status/
```

Важно: штатный docs-site слушает HTTP, а не HTTPS. URL `https://localhost:4321/` не является ожидаемым endpoint.

## Fix Actions

`scripts/fix-server` обслуживает локальные dashboard кнопки на `127.0.0.1:4322` и вызывает `scripts/apply-fix`.

`scripts/apply-fix` - allowlisted executor для operational fixes, которые запускаются из dashboard или CLI. Он не принимает произвольные shell-команды.

Project-scoped fix actions, например `rag.reindex`, используют обычные project configs, namespace isolation, exclude rules и secret scan. Runtime fix actions ограничены управлением описанным `launchd` supervisor.

## Source Of Truth

- `docs/` - source-документация хаба.
- `docs-site/src/content/docs/` - web-представление и hand-authored site pages.
- Подключенные проекты - source-документация своих проектов.
- `storage/index`, `storage/generated`, `docs-site/public/llms*.txt`, generated project pages, runtime logs и heartbeats - derived artifacts.
