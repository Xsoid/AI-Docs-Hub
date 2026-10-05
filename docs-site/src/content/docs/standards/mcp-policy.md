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

`get_project_context` возвращает компактный read-only manifest одного namespace: profile, docs index/readiness status, bounded metadata root/nested `AGENTS.md` и `CLAUDE.md`, каталог skills без содержимого, quality/capability status, `context_fingerprint` и deterministic `recommended_next_tools`. Manifest не является dump документации и не preload-ит source files.

`read_project_instruction` принимает только project-relative path, ранее найденный manifest discovery. Он не превращается в общий filesystem reader: применяются `safe_resolve`, configured/default excludes, project-root containment, secret scan и лимит `250_000` bytes; содержимое выдаётся только on-demand с `content_hash` и `truncated`.

`capture_project_context` и `check_project_context` работают project-scoped и read-only. Snapshot хранится в ignored `storage/context-snapshots/<project>/<snapshot-id>.json` и содержит только deterministic digests, статусы и безопасные metadata: source contents, raw diff, queries и credentials туда не записываются. Freshness states: `fresh`, `stale`, `degraded`, `missing`; неизвестный или недоступный optional Codebase Memory попадает в `unknown_components` и не считается подтвержденным fresh.

Все `tools/call` Hub и Codebase Memory proxy имеют общий sanitized audit contract в ignored `storage/mcp-audit/YYYY-MM-DD.jsonl`. Записываются только safe project id, tool/class, duration, status, error category, result size и явные allowlisted metadata. Raw arguments, query, source paths, contents, snippets, diff, findings, credentials, headers, environment и exception messages не записываются. `get_mcp_usage_summary` возвращает bounded aggregate и не считает собственный summary call; audit остается локальным и не является внешней telemetry.

## Confirmation Rules

`index_project` не запускает indexing без `confirm=true`. Safe default возвращает risk, command и пример MCP call.

`scaffold_project_docs` не пишет files в connected project root без `confirm=true`. Dry-run остается default.

Skill Intelligence read tools project-scoped и не переключают namespace. `get_project_profile` также возвращает компактный Skill Intelligence summary, но не заменяет полный audit. Audit сравнивает workflow-кандидаты по содержимому между разными sources и проверяет ownership skill-сегментов относительно canonical docs/`AGENTS.md`; project-derived текст в summary не копируется. Proposal/audit artifacts сохраняются локально в ignored storage. `apply_skill_proposal` принимает complete reviewed content только для точного набора proposal targets; без `confirm=true` он возвращает dry-run и ничего не записывает. Apply повторно проверяет project-root containment, allowed path surface, exclude rules, secret patterns и hash исходного файла. Hub не вызывает LLM для proposal transformation или генерации skills.

## Project Lifecycle Tools

MCP project lifecycle tools не запускают LLM. get_quality_profile и verify_patch выполняют только deterministic discovery/checks; prepare_patch_review возвращает diff-first metadata; record_code_review и record_security_review принимают explicit structured results только при совпадении текущего fingerprint; get_pre_publish_status читает gate state; onboard_project требует confirm=true и пишет только managed block в external project AGENTS.md. Reports хранятся в ignored storage/project-lifecycle/<project>/.

Security review является отдельным record и не является alias code review. Допустимая положительная формулировка — no findings in reviewed scope; absolute security guarantee запрещена.

## Config Edits

Global `~/.codex/config.toml` можно редактировать только когда задача требует Codex/MCP setup. Правки должны быть scoped и явно описаны пользователю.

Project files считаются read-only, кроме explicit scaffold и Skill Intelligence proposal workflows с `confirm=true`.

Подключение отдельного проекта к локальному Hub, включая project-scoped MCP entry и managed routing rules, не является изменением source documentation Hub. Такой onboarding не должен создавать tracked-файлы в `docs/`, `docs-site/` или `docs/changes/`. Change note нужен только для изменения самой политики или реализации этого workflow.

## Codebase Memory Sidecar

Codebase Memory работает как отдельный project-scoped MCP server через `mcp/codebase_memory_proxy.py --project project-name`; он не расширяет список tools основного `mcp/server.py`.

Proxy публикует только read-oriented tools, закрепляет каждый call за project из `--project` и блокирует mutating tools, cross-project calls и repository persistence. MCP entry создается отдельно как `codebase_<project>`, а после изменения `~/.codex/config.toml` Codex необходимо перезапустить. См. практическое руководство [Codebase Memory](/hub/codebase-memory/).
