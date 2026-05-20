# 2026-05-20 - Hub Stack Map And Documentation Duty

## Что Изменилось

Архитектура хаба получила явную карту стеков:

- Python 3.11;
- Node.js 22/npm 10;
- Astro/Starlight;
- Markdown docs-as-code;
- YAML project config;
- MkDocs adapter;
- Lite JSON/BM25 RAG;
- MCP stdio bridge;
- local runtime и macOS `launchd`;
- optional Swift/AppKit menu bar app;
- generated artifacts.

Корневые agent rules теперь явно требуют дорабатывать документацию хаба в том же изменении, если меняются архитектура, RAG, MCP, docs-site, indexing, generated context, runtime, operations, project config behavior, stack dependencies или agent workflow.

## Поведение

Агенты не должны оставлять документацию хаба как follow-up, если изменение вводит новый concept, command, status field, dependency или operational workflow.

## Проверка

Выполнены:

- `./scripts/docs-npm run build`;
- `git diff --check`.
