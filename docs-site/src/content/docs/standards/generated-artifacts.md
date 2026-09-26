---
title: Generated Artifacts
description: Derived files, ownership rules and regeneration commands.
---

Generated artifacts являются производными от docs-as-code и configs.

## Artifacts

- `storage/index/*.json`;
- `storage/index/*_log.jsonl`;
- `storage/generated/*`;
- `docs-site/public/llms*.txt`;
- `docs-site/src/content/docs/projects/*`;
- `docs-site/dist/`;
- `storage/runtime/*`;
- `storage/logs/*`;
- `build/AI Docs Hub.app`.
- `storage/runtime/bin/codebase-memory-mcp` и `storage/codebase-memory/*`.
- `storage/skill-intelligence/<project>/*` — project-derived skill inventory, audits и proposals; artifacts не коммитятся и не зеркалируются в docs-site.

## Правила

- Не редактировать generated artifacts вручную как source documentation.
- Source changes должны вноситься в `docs/`, `docs-site/src/content/docs/`, project docs или configs.
- Generated artifacts можно пересоздавать командами `make project-pages`, `make llms`, `make index`, `make docs-build`.
- Allowlisted fix action `rag.reindex` пересоздает project index и после успешной индексации запускает regeneration `llms*.txt`.
- Generated project pages являются web-представлением configs/index/readiness, а не source docs проекта.
- Skill Intelligence inventory, audit и proposal JSON являются local-only derived artifacts. Для внешнего проекта их единственное Hub-хранилище — ignored `storage/skill-intelligence/<project>/`; apply пишет только в разрешенные paths внутри внешнего project root.

## Status

`hub-status` проверяет generated context:

- наличие `llms*.txt` в public и storage mirrors;
- наличие `llms-report.json`;
- наличие generated overview page для каждого real project config.

Missing generated artifacts являются operational warning.
