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

## Правила

- Не редактировать generated artifacts вручную как source documentation.
- Source changes должны вноситься в `docs/`, `docs-site/src/content/docs/`, project docs или configs.
- Generated artifacts можно пересоздавать командами `make project-pages`, `make llms`, `make index`, `make docs-build`.
- Generated project pages являются web-представлением configs/index/readiness, а не source docs проекта.

## Status

`hub-status` проверяет generated context:

- наличие `llms*.txt` в public и storage mirrors;
- наличие `llms-report.json`;
- наличие generated overview page для каждого real project config.

Missing generated artifacts являются operational warning.
