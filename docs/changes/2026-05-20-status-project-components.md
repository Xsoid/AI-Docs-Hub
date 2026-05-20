# 2026-05-20 - Status Project Components

## Что Изменилось

`/status/` теперь показывает больше компонентов хаба и project-scoped diagnostics для тех слоев, где это имеет смысл:

- `Проекты` - project config, source discovery, docs backend и project agent rules;
- `Generated context` - `llms*.txt` и generated project overview pages;
- `Поиск по документам` - RAG backend, source files, indexed documents, chunks, freshness, newest source timestamp и index path по каждому проекту;
- `MkDocs` - backend/config/docs_dir по проектам;
- `Документация` - documentation coverage и scaffold availability по проектам.

Глобальные компоненты остаются глобальными: runtime, docs-site, repository health, MCP и watcher.

## Поведение

Documentation readiness recommendations остаются рекомендациями и не переводят общий статус в degraded. Missing или stale RAG indexes и missing generated artifacts отображаются как warning, потому что они влияют на доступность или актуальность поиска/generated context.

## Проверка

Выполнены:

- `python3.11 -m py_compile scripts/hub-status`;
- `python3.11 scripts/hub-status --json`;
- `curl http://localhost:4321/api/hub-status.json`;
- `./scripts/docs-npm run build`;
- `git diff --check`.
