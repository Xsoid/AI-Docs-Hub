# Codebase Memory

Codebase Memory подключается к AI Docs Hub как optional sidecar для структурного анализа исходного кода. Он не заменяет Lite RAG, docs-as-code, project configs, `llms*.txt` или Hub MCP.

## Граница Ответственности

- AI Docs Hub ищет документацию, ADR, runbooks и project policies.
- Codebase Memory ищет symbols, calls, imports, routes, dependencies и blast radius.
- Markdown ADR внутри проекта остается source of truth. `manage_adr` Codebase Memory не используется.
- Hub wrapper разрешает только read-oriented query tools и блокирует `manage_adr`, `delete_project`, `ingest_traces` и прямой `index_repository`.
- Cross-project wildcard не используется без прямого запроса пользователя.

## Локальное Хранение

Hub-managed binary и SQLite cache хранятся только в ignored runtime paths:

```text
storage/runtime/bin/codebase-memory-mcp
storage/codebase-memory/
```

Эти файлы являются derived local artifacts и не коммитятся. Connected project не получает `.codebase-memory/graph.db.zst` или изменения `.gitattributes`: wrapper всегда передает `persistence=false`.

## Установка И Индексирование

```sh
make codebase-memory-install
make codebase-memory-index PROJECT=project-name
make codebase-memory-status PROJECT=project-name
```

Installer запускается с `--skip-config`, поэтому он не меняет agent instructions, hooks или MCP configs. MCP entry добавляется вручную через `mcp/codebase_memory_proxy.py --project project-name`, использует `CBM_CACHE_DIR` внутри ignored `storage/`, фиксирует project scope и не публикует mutating tools агенту.

Индексирование explicit-only: `auto_index=false`, `auto_watch=false`. Wrapper разрешает режимы `fast`, `moderate` и `full`, но штатная Make-команда использует `moderate`.

## Security Gate

Перед индексированием в root подключенного проекта должен существовать `.cbmignore`. Wrapper проверяет обязательные exclusions для `.env`, secret/token/password/credential paths, cookies, sessions, dumps и private keys.

`.cbmignore` является project-owned source-файлом и должен храниться в самом подключенном проекте. Project config остается локальным binding и не коммитится в Hub. Индекс и binary остаются только в ignored `storage/` Hub.

## Status

`scripts/hub-status` публикует optional component `codebase-memory` с version, cache path и найденными project graphs. `make codebase-memory-status` сохраняет ignored snapshot в `storage/runtime/codebase-memory`; dashboard читает snapshot и не конкурирует с MCP за SQLite. Отсутствие binary или графов переводит общий status в `DEGRADED`, но не в `DOWN`.

Dashboard показывает этот компонент на `http://localhost:4321/status/` как «Граф исходного кода».
