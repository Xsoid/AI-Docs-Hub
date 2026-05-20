# Справочник Команд

Эта страница собирает основные команды AI Docs Hub и связывает их с runtime/workflow-ами.

## Setup И Проверки

| Команда | Назначение |
| --- | --- |
| `make setup` | Создать `.venv`, установить docs-site npm dependencies, сгенерировать project pages и проверить configs. |
| `make healthcheck` | Проверить структуру репозитория, runtimes, storage, configs и Lite RAG backend. |
| `make validate-configs` | Проверить `configs/projects/*.yaml` без запуска runtime. |
| `make mcp-test` | Проверить stdio MCP handshake, tools list и MCP `healthcheck`. |

`healthcheck` не доказывает, что docs-site слушает порт. Для live runtime используйте `make hub-status`.

## Docs-Site И Runtime

| Команда | Назначение |
| --- | --- |
| `make docs-dev` | Сгенерировать project pages и запустить Astro dev server. |
| `make docs-build` | Сгенерировать project pages и собрать static docs-site. |
| `make hub-dev` | Запустить docs-site и watcher вместе в foreground. |
| `make hub-status` | Проверить live runtime, docs-site, repository, projects, generated context, RAG, MkDocs, docs readiness, MCP и watcher. |

Штатный URL docs-site:

```text
http://localhost:4321/
```

`https://localhost:4321/` не является ожидаемым endpoint.

## Persistent Runtime На macOS

| Команда | Назначение |
| --- | --- |
| `make hub-install` | Установить user LaunchAgent `local.ai-docs-hub.runtime`. |
| `make hub-start` | Запустить LaunchAgent. |
| `make hub-stop` | Остановить LaunchAgent. |
| `make hub-restart` | Перезапустить LaunchAgent. |
| `make hub-launchd-status` | Показать, установлен и загружен ли service. |
| `make hub-logs` | Показать runtime logs из `storage/logs`. |
| `make hub-uninstall` | Остановить service и удалить plist. |

## macOS Menu Bar

| Команда | Назначение |
| --- | --- |
| `make hub-menu-build` | Собрать `build/AI Docs Hub.app`. |
| `make hub-menu-start` | Собрать при необходимости и открыть menu bar helper. |
| `make hub-menu-status` | Показать, запущен ли helper. |
| `make hub-menu-stop` | Закрыть helper. |
| `make hub-menu-restart` | Пересобрать и перезапустить helper. |

## Generated Context

| Команда | Назначение |
| --- | --- |
| `make project-pages` | Сгенерировать derived project pages в docs-site. |
| `make llms` | Сгенерировать `llms.txt`, `llms-full.txt`, `llms-small.txt` и report. |

Generated artifacts не редактируются вручную.

## RAG И Watcher

| Команда | Назначение |
| --- | --- |
| `make index PROJECT=name` | Построить Lite RAG index одного проекта. |
| `make reindex PROJECT=name` | Удалить существующий index и построить заново. |
| `make index-all` | Индексировать все валидные project configs. |
| `make watch PROJECT=name` | Следить за одним проектом и переиндексировать при изменениях. |
| `make watch-all` | Следить за всеми watchable проектами. |
| `make check-secrets PROJECT=name` | Проверить разрешенные files проекта на secret-looking paths/content. |

Индексация пишет локальные JSON/BM25 indexes в `storage/index`.

## Documentation Quality

| Команда | Назначение |
| --- | --- |
| `make lint PROJECT=name` | Проверить broken wiki-links, orphan pages, empty docs, duplicate headings и documentation readiness. |
| `make scaffold-docs PROJECT=name` | Dry-run плана starter docs для проекта. |
| `make scaffold-docs-write PROJECT=name` | Явно создать missing starter docs в подключенном проекте. |
| `make logs PROJECT=name` | Прочитать operation log проекта из `storage/index/{project}_log.jsonl`. |

`scaffold-docs-write` является явным разрешением на запись в connected project root. Non-empty files не перезаписываются.

## MCP Tools

`mcp/server.py` exposes:

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

`index_project` требует `confirm=true`, чтобы начать indexing через MCP. `scaffold_project_docs` требует `confirm=true`, чтобы писать files в подключенный проект.

## Cleanup

| Команда | Назначение |
| --- | --- |
| `make clean-cache` | Удалить `docs-site/dist`, npm cache, generated files и Python `__pycache__`. |

Удаление `storage/index/{project}.json` удаляет локальный RAG index и не трогает проект.
