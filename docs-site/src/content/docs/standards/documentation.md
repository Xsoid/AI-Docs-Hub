---
title: Documentation Standard
description: Docs-as-code ownership, hub documentation duty and project documentation readiness.
---

Документация является частью definition of done для изменений AI Docs Hub.

## Правило

Каждое значимое изменение хаба должно обновлять source-документацию в `docs/` и matching docs-site content в `docs-site/src/content/docs/`.

Это строгое non-negotiable правило, которое нельзя игнорировать. Нельзя завершать изменение хаба, оставляя документацию follow-up.

Это включает изменения в:

- RAG behavior;
- MCP tools или protocol behavior;
- docs-site behavior;
- правилах индексации;
- generated context files;
- runtime commands;
- commands;
- status fields;
- launch или supervision behavior;
- project config behavior;
- agent workflow;
- stack dependencies;
- operational workflows.

Если документацию нельзя обновить в том же change, реализация считается незавершенной и это нужно явно сообщить.

## Git Workflow

Изменения AI Docs Hub выполняются непосредственно в `main`. Агенты не создают отдельные feature-, task- или agent-ветки, если пользователь явно не отменил это правило для конкретной задачи.

## Каталог Стандартов

- [Documentation](/standards/documentation/) - docs-as-code ownership, hub documentation duty, change notes и readiness.
- [Project Config](/standards/project-config/) - portable roots, namespaces, `sources`, `include`, `exclude`, `agent_rules`, `docs_backend` и `mkdocs_config`.
- [Source Discovery](/standards/source-discovery/) - effective source plan, standard sources и safe MkDocs structural discovery.
- [RAG Policy](/standards/rag-policy/) - local indexing, namespaces, secret-safe filtering, output metadata, watch mode и freshness.
- [MCP Policy](/standards/mcp-policy/) - stdio JSON-RPC, project scoping, stderr logging и confirmation rules.
- [llms.txt](/standards/llms-txt/) - generated LLM context files, inputs, outputs и manual-edit restrictions.
- [Runtime Status](/standards/runtime-status/) - healthcheck vs live runtime, `hub-status`, status codes и local URLs.
- [Status Diagnostics](/standards/status-diagnostics/) - components, required/optional semantics и JSON contract.
- [Scaffold](/standards/scaffold/) - dry-run default, explicit writes и non-overwrite behavior.
- [Generated Artifacts](/standards/generated-artifacts/) - derived files and ownership rules.
- [Security](/standards/security/) - secret hygiene, path safety and namespace isolation.

Если новое поведение хаба не ложится в одну из этих групп, добавьте или расширьте standard section до того, как считать поведение установленным.

## Подключенные Проекты

Хаб должен подталкивать проект к достаточной документационной структуре, но не должен ломать поиск только из-за неполной документации.

Recommended project docs:

- `README.md`;
- `AGENTS.md`;
- `docs/index.md`;
- `docs/architecture/`;
- `docs/modules/`;
- `docs/decisions/`;
- `docs/api/`;
- `docs/deployment/`;
- `docs/operations/`;
- `docs/infrastructure/`;
- `docs/configuration.md`;
- `docs/security.md`;
- `docs/data.md`;
- `docs/integrations.md`;
- `docs/observability.md`;
- `docs/testing.md`;
- `docs/troubleshooting.md`;
- `docs/development.md`;
- `docs/glossary.md`.

Если проект использует MkDocs, `docs_dir` из `mkdocs.yml` заменяет standard `docs/` как root рекомендаций.

## Documentation Readiness

Missing or empty sections являются recommendations, не config errors.

Readiness считает:

- общий documentation coverage percent;
- category coverage для `core`;
- category coverage для `technical`;
- recommendations count;
- scaffold availability.

Documentation readiness recommendations не являются operational health failure.

Documentation lint проверяет duplicate headings по реальным Markdown heading lines внутри indexed text. Повторение одного `heading` в metadata нескольких RAG chunks длинного раздела не является duplicate heading.

## Change Notes

Добавляйте файл в `docs/changes/`, когда изменение влияет на usage, operations, debugging или extension.

Change note должен содержать:

- дату;
- краткое описание;
- измененное поведение;
- выполненную проверку;
- follow-up, если он есть.

## Generated Files

Не редактируйте derived artifacts вручную как source-документацию. См. [Generated Artifacts](/standards/generated-artifacts/).

## Path Portability

В source docs и committed configs не должно быть hard-coded absolute paths к конкретной машине.

Используйте:

- `<AI_DOCS_HUB_ROOT>` для команд;
- `<EXTERNAL_PROJECT_ROOT>` для external projects;
- `${AI_DOCS_PROJECTS_ROOT}/project-name` в project configs;
- `__AI_DOCS_HUB_ROOT__` и `__PYTHON3_11__` в templates.

## Secrets

Никогда не документируйте secrets, credentials, tokens, cookies, private keys, sessions, dumps или secret-looking values.
