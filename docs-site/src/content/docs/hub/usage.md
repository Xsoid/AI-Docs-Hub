---
title: Использование
description: Основные workflows для setup, runtime, docs-site, llms, RAG и MCP.
---

## Setup

```sh
make setup
make healthcheck
make mcp-test
```

`make setup` создает `.venv`, устанавливает npm dependencies для docs-site и валидирует project configs. Python dependencies сейчас входят в standard library.

## Запуск Хаба

Рекомендуемый foreground runtime:

```sh
make hub-dev
```

Он запускает docs-site и watcher вместе, пишет heartbeat в `storage/runtime/hub-dev.status.json` и останавливает дочерние процессы при завершении.

Persistent runtime на macOS:

```sh
make hub-install
make hub-start
make hub-status
```

Остановить:

```sh
make hub-stop
```

Docs-site доступен по HTTP:

```text
http://localhost:4321/
```

`https://localhost:4321/` не является штатным URL.

## Status

CLI:

```sh
make hub-status
```

Dashboard:

```text
http://localhost:4321/status/
```

Status проверяет runtime, docs-site, repository health, project configs, generated context, RAG indexes, MkDocs adapter, documentation readiness, MCP bridge и watcher heartbeat.

## Project Config

Project configs живут в:

```text
configs/projects/*.yaml
```

Минимальная форма:

```yaml
project: my-project
namespace: my-project
title: "My Project"
root: "${AI_DOCS_PROJECTS_ROOT}/my-project"
docs_backend: auto
mkdocs_config: "mkdocs.yml"

sources:
  - path: "docs"
    type: markdown

include:
  - "docs/**/*.md"
  - "README.md"
  - "AGENTS.md"

exclude:
  - ".git/**"
  - "node_modules/**"
  - ".env"
  - ".env.*"
  - "**/*secret*"
  - "**/*token*"
  - "**/*.key"
  - "**/*.pem"
```

Проверить:

```sh
make validate-configs
```

## Generated Project Pages

```sh
make project-pages
```

Generated project pages пишутся в `docs-site/src/content/docs/projects/*` и не редактируются вручную.

## llms.txt

```sh
make llms
```

Команда генерирует `llms.txt`, `llms-full.txt`, `llms-small.txt` в `docs-site/public/` и `storage/generated/`.

## RAG

Индексировать один проект:

```sh
make index PROJECT=my-project
```

Полная переиндексация:

```sh
make reindex PROJECT=my-project
```

Все проекты:

```sh
make index-all
```

Watcher:

```sh
make watch PROJECT=my-project
make watch-all
```

Перед индексированием выполняется secret scan. Если найден suspicious path или content, index write блокируется.

## Documentation Quality

Проверить структуру docs проекта:

```sh
make lint PROJECT=my-project
```

Посмотреть план недостающих recommended docs:

```sh
make scaffold-docs PROJECT=my-project
```

Создать недостающие starter-файлы в подключенном проекте:

```sh
make scaffold-docs-write PROJECT=my-project
```

Dry-run не пишет проектные файлы. Write mode является явным разрешением на изменение подключенного проекта.

## MCP

Запустить MCP server напрямую:

```sh
make mcp-dev
```

Проверить MCP handshake/tools:

```sh
make mcp-test
```

Project-scoped запуск:

```sh
python3.11 mcp/server.py --project my-project
```

MCP tools:

- `list_projects`;
- `get_project_profile`;
- `search_docs`;
- `read_doc`;
- `search_decisions`;
- `search_modules`;
- `index_project`;
- `healthcheck`;
- `lint_project`;
- `scaffold_project_docs`;
- `read_operation_log`.

`index_project` и `scaffold_project_docs` требуют `confirm=true` для действий, которые пишут локальный index или проектные files.

## Logs

Operation logs:

```sh
make logs PROJECT=my-project
```

Persistent runtime logs:

```sh
make hub-logs
```

Подробный список команд: [Справочник команд](/hub/command-reference/).
