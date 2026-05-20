---
title: Agent Rules
description: Rules for agents using the hub.
---

Эти правила применяются к агентам, которые используют AI Docs Hub.

## Изоляция Проектов

- Не смешивать context из разных проектов без прямого запроса пользователя.
- Каждый MCP/RAG search должен оставаться в project namespace.
- Если project context не найден, явно сказать, что поиск не вернул matching context.

## Secret Safety

- Не индексировать `.env`, private keys, credentials, tokens, cookies, sessions, dumps или secret-looking files.
- Не возвращать content, если secret scan нашел suspicious pattern.
- Не документировать реальные secrets или production values.

## Connected Projects

- Подключенные проекты считаются read-only.
- Запись в проект допустима только через явное действие: `make scaffold-docs-write` или MCP `scaffold_project_docs` с `confirm=true`.
- Non-empty project files нельзя перезаписывать scaffold-ом.

## Source Of Truth

- RAG index и `llms*.txt` являются derived artifacts.
- Source of truth для хаба - `docs/` и hand-authored docs-site pages.
- Source of truth для проекта - документация внутри самого проекта.

## Codex И MCP

- Global `~/.codex/config.toml` можно редактировать, когда задача требует Codex/MCP setup.
- Такие правки должны быть scoped и явно описаны пользователю.
- MCP stdout зарезервирован для JSON-RPC messages; logs идут в stderr.

## Documentation Duty

Hub documentation is part of the implementation. This rule is non-negotiable and must never be ignored.

Если изменение AI Docs Hub затрагивает architecture, RAG, MCP, docs-site, indexing, generated context, runtime, operations, project config behavior, stack dependencies, commands, status fields или agent workflow, нужно обновить в том же change:

- source docs в `docs/`;
- matching docs-site content в `docs-site/src/content/docs/`;
- change note в `docs/changes/`, если поведение влияет на usage, operations, debugging или extension.

Нельзя завершать изменение хаба, оставляя документацию follow-up. Если документацию нельзя обновить в том же change, реализация считается незавершенной.

Если documentation и code конфликтуют, нужно указать оба source paths и исправить конфликт вместо того, чтобы скрывать расхождение.
