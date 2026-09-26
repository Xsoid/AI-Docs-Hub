---
title: MCP Policy
description: MCP stdio bridge behavior, project scoping and write confirmation rules.
---

MCP bridge работает как локальный stdio JSON-RPC server.

## Runtime

```sh
python3.11 mcp/server.py
python3.11 mcp/server.py --project project-name
```

Stdout зарезервирован для MCP JSON-RPC messages. Logs должны идти в stderr.

## Scope

- Без `--project` каждый tool call должен явно передавать `project`, если tool project-scoped.
- С `--project` server фиксирует active project и отклоняет попытки вызвать другой project.
- Tools не должны смешивать namespaces между проектами.

## Tools

Текущий набор:

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
- `read_operation_log`;
- `analyze_skill_candidates`;
- `get_skill_inventory`;
- `get_skill_proposal`;
- `validate_skill_architecture`;
- `create_skill_proposal`;
- `create_skill_evolution_proposal`;
- `apply_skill_proposal`.

## Confirmation Rules

`index_project` не запускает indexing без `confirm=true`. Safe default возвращает risk, command и пример MCP call.

`scaffold_project_docs` не пишет files в connected project root без `confirm=true`. Dry-run остается default.

Skill Intelligence read tools project-scoped и не переключают namespace. `get_project_profile` также возвращает компактный Skill Intelligence summary, но не заменяет полный audit. Audit сравнивает workflow-кандидаты по содержимому между разными sources и проверяет ownership skill-сегментов относительно canonical docs/`AGENTS.md`; project-derived текст в summary не копируется. Proposal/audit artifacts сохраняются локально в ignored storage. `apply_skill_proposal` принимает complete reviewed content только для точного набора proposal targets; без `confirm=true` он возвращает dry-run и ничего не записывает. Apply повторно проверяет project-root containment, allowed path surface, exclude rules, secret patterns и hash исходного файла. Hub не вызывает LLM для proposal transformation или генерации skills.

## Config Edits

Global `~/.codex/config.toml` можно редактировать только когда задача требует Codex/MCP setup. Правки должны быть scoped и явно описаны пользователю.

Project files считаются read-only, кроме explicit scaffold и Skill Intelligence proposal workflows с `confirm=true`.

Подключение отдельного проекта к локальному Hub, включая project-scoped MCP entry и managed routing rules, не является изменением source documentation Hub. Такой onboarding не должен создавать tracked-файлы в `docs/`, `docs-site/` или `docs/changes/`. Change note нужен только для изменения самой политики или реализации этого workflow.

## Codebase Memory Sidecar

Codebase Memory работает как отдельный project-scoped MCP server через `mcp/codebase_memory_proxy.py --project project-name`; он не расширяет список tools основного `mcp/server.py`.

Proxy публикует только read-oriented tools, закрепляет каждый call за project из `--project` и блокирует mutating tools, cross-project calls и repository persistence. MCP entry создается отдельно как `codebase_<project>`, а после изменения `~/.codex/config.toml` Codex необходимо перезапустить. См. практическое руководство [Codebase Memory](/hub/codebase-memory/).
