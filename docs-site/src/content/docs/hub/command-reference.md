---
title: Справочник Команд
description: Команды AI Docs Hub по setup, runtime, RAG, MCP, scaffold и generated context.
---

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
| `python3.11 scripts/fix-server` | Запустить local allowlisted fix action server на `127.0.0.1:4322`. |

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
| `python3.11 scripts/apply-fix --action rag.reindex --project name` | Allowlisted repair action: переиндексировать project namespace и регенерировать `llms*.txt`. |
| `make index-all` | Индексировать все валидные project configs. |
| `make watch PROJECT=name` | Следить за одним проектом, переиндексировать при изменениях и обновлять read-only Skill Intelligence audit. |
| `make watch-all` | Следить за всеми watchable проектами, включая автоматическое обновление Skill Intelligence audit. |
| `make check-secrets PROJECT=name` | Проверить разрешенные files проекта на secret-looking paths/content. |

Индексация пишет локальные JSON/BM25 indexes в `storage/index`.

Для намеренного отключения автоматического audit запустите `scripts/watch-project --all --no-skill-audit`; status тогда честно покажет stale audit после изменения источников.

`scripts/apply-fix` принимает только allowlisted actions. Для runtime доступны `docs-site.restart`, `runtime.start` и `runtime.install-start`; из dashboard они запускаются как фоновые jobs через `/api/apply-fix.json`.

## Documentation Quality

| Команда | Назначение |
| --- | --- |
| `make lint PROJECT=name` | Проверить документацию и skill architecture: ссылки, пустые docs, дубликаты, readiness и skill validation. |
| `make scaffold-docs PROJECT=name` | Dry-run плана starter docs для проекта. |
| `make scaffold-docs-write PROJECT=name` | Явно создать missing starter docs в подключенном проекте. |
| `make skill-audit PROJECT=name` | Выполнить read-only Skill Architecture audit с локальным JSON report в ignored storage. |
| `python3.11 scripts/skill-audit --project name --json` | Вернуть machine-readable skill inventory, workflow candidates и validation diagnostics. |
| `python3.11 scripts/apply-fix --action skill-audit --project name` | Allowlisted dashboard action: выполнить read-only audit и обновить локальный report. |
| `make logs PROJECT=name` | Прочитать operation log проекта из `storage/index/{project}_log.jsonl`. |

`scaffold-docs-write` является явным разрешением на запись в connected project root. Non-empty files не перезаписываются.

`skill-audit` не меняет project files. Skill proposals также ничего не меняют, пока Codex не передаст reviewed content и `confirm=true` в `apply_skill_proposal`. Результаты внешнего проекта хранятся только локально в `storage/skill-intelligence/<project>/`.

`get_project_profile` возвращает компактный `skill_intelligence` summary с inventory status, числом skills/candidates, high-confidence candidates, validation counts и временем последнего сохраненного audit; полный machine-readable report остается доступен через Skill Intelligence audit tools.

## MCP Tools

Для проверки состояния контекста доступны project-scoped MCP tools `capture_project_context` и `check_project_context`. Они используют metadata-only snapshots в ignored `storage/context-snapshots/<project>/`; source contents и raw diff не сохраняются.

`get_mcp_usage_summary` возвращает bounded aggregate локального sanitized audit trail по project/tool/server без raw arguments и результатов.

`mcp/server.py` exposes:

- `list_projects`;
- `get_project_profile`;
- `get_project_context`;
- `read_project_instruction`;
- `capture_project_context`;
- `check_project_context`;
- `get_mcp_usage_summary`;
- `search_docs`;
- `read_doc`;
- `search_decisions`;
- `search_modules`;
- `index_project`;
- `healthcheck`;
- `lint_project`;
- `scaffold_project_docs`;
- `read_operation_log`;
- `analyze_skill_candidates`;
- `get_skill_inventory`;
- `get_skill_proposal`;
- `validate_skill_architecture`;
- `create_skill_proposal`;
- `create_skill_evolution_proposal`;
- `apply_skill_proposal`.

`index_project` требует `confirm=true`, чтобы начать indexing через MCP. `scaffold_project_docs` требует `confirm=true`, чтобы писать files в подключенный проект.

## Project Lifecycle / Quality Gate

| Команда | Назначение |
| --- | --- |
| make project-onboard PROJECT=name | Явно добавить или обновить только Hub-managed lifecycle block в project AGENTS.md. |
| make quality-profile PROJECT=name | Построить machine-readable profile существующих project checks. |
| make verify-patch PROJECT=name SCOPE=working | Выполнить deterministic checks, git diff check и secret scan. |
| make prepare-review PROJECT=name KIND=code | Подготовить compact diff-first metadata для explicit code/security review. |
| make pre-publish PROJECT=name SCOPE=staged | Проверить state machine и publishable status текущего fingerprint. |
| make review-status PROJECT=name | Прочитать lifecycle status без запуска semantic review. |

Semantic review records пишутся через MCP tools record_code_review и record_security_review. Старый fingerprint не переносится после изменения patch. Reports external projects остаются в ignored storage/project-lifecycle.

## Codebase Memory

| Команда | Назначение |
| --- | --- |
| `make codebase-memory-install` | Установить hub-managed binary в ignored `storage/runtime/bin/` без изменения MCP config. |
| `make codebase-memory-index PROJECT=name` | Явно построить project-scoped graph в режиме `moderate` с `persistence=false`; требует безопасный `.cbmignore`. |
| `make codebase-memory-status PROJECT=name` | Проверить binary, graph, project-scoped MCP config, managed agent rules и `fully_connected`. |
| `python3.11 scripts/apply-fix --action codebase-memory.index --project name` | Идемпотентно подготовить `.cbmignore`, построить graph, настроить отдельный MCP server и routing rules. |

После первого onboarding или изменения MCP config перезапустите Codex. Полная модель использования и список read-only tools описаны на странице [Codebase Memory](/hub/codebase-memory/).

## Cleanup

| Команда | Назначение |
| --- | --- |
| `make clean-cache` | Удалить `docs-site/dist`, npm cache, generated files и Python `__pycache__`. |

Удаление `storage/index/{project}.json` удаляет локальный RAG index и не трогает проект.
