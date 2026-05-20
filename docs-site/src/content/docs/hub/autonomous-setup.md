---
title: Autonomous Setup
description: Local runtime dependencies for running AI Docs Hub without Docker.
---

AI Docs Hub работает как локальный автономный toolchain. Для docs-site, Lite RAG, `llms*.txt`, MCP, indexing, lint, scaffold и watch mode Docker не нужен.

## Требования

На host machine должны быть доступны:

- Python 3.11 available as `python3.11`;
- Node.js 22 LTS available as `node`;
- npm 10+ available as `npm`;
- Git;
- `make`.

On macOS with Homebrew:

```sh
brew install python@3.11 node@22
brew link --force --overwrite node@22
```

`python3` на macOS может указывать на старый system Python. Команды хаба намеренно используют `python3.11`.

## Локальная Настройка

Из корня хаба:

```sh
make setup
make healthcheck
make llms
make mcp-test
```

`make setup` создает `.venv`, устанавливает docs-site npm dependencies и валидирует project configs. Python dependencies сейчас standard-library only.

## Роли Runtime

- Python runs Lite RAG, MCP, indexing, lint, healthcheck, `llms*.txt`, and watch mode.
- Node/npm run the Astro Starlight docs site.
- `storage/` keeps local indexes, generated files, and operation logs.
- `configs/projects/*.yaml` connects external project documentation through resolvable portable roots, such as `${AI_DOCS_PROJECTS_ROOT}/project-name`.

## Что Не Нужно

Docker is not a default runtime dependency. The hub does not require Docker Compose, RAGFlow, cloud vector databases, or external AI APIs for normal operation.

Global Codex config can be configured for MCP access. Use `codex-config.example.toml` or `project-codex-config.example.toml` as templates and keep applied edits scoped.

## Проверка После Setup

```sh
make hub-status
```

`healthcheck` проверяет repository prerequisites, но не доказывает, что docs-site прямо сейчас слушает порт. Для live runtime используйте `hub-status` или `/status/`.
