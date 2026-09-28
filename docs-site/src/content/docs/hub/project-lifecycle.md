---
title: Project Lifecycle / Quality Gate
description: Локальный onboarding, deterministic verification, fingerprint и отдельные code/security review перед публикацией patch.
---

# Project Lifecycle / Quality Gate

AI Docs Hub предоставляет локальный lifecycle для patch подключенного проекта. Hub отвечает за metadata, deterministic checks, fingerprint и gate state. Semantic code review и security review выполняются только явным Codex workflow и записываются обратно через MCP.

## Границы и переиспользование

Lifecycle использует существующие ProjectConfig, safe path/secret scan, project namespace, Codebase Memory, Skill Intelligence и ignored storage. Он не создает второй project discovery, RAG, security scanner или skill workflow.

Установленная версия Codex CLI предоставляет native non-interactive review через codex review, но отдельного non-interactive init subcommand не предоставляет. Поэтому onboarding не эмулирует TUI: он сохраняет пользовательский AGENTS.md и добавляет только узкий managed block. Native Codex review запускается явно.

## Команды

    python3.11 scripts/onboard-project --project name --write
    python3.11 scripts/quality-profile --project name
    python3.11 scripts/verify-patch --project name --scope working --json
    python3.11 scripts/pre-publish --project name --scope staged

Onboarding идемпотентно сохраняет custom AGENTS content, добавляет только managed lifecycle block и возвращает restart_required=true после записи. Verification всегда выполняет git diff --check и secret scan, а найденные project commands выполняет с timeout. Reports содержат metadata и digests, без source snippets и абсолютных project paths.

## Fingerprint, reviews и gate

Fingerprint учитывает repository identity hash, scope, base, HEAD, changed files, staged/unstaged diff и relevant untracked bytes. Поддерживаются working, staged, range и branch. Любое изменение patch делает старые results stale.

Code review и security review — независимые MCP records, привязанные к fingerprint. Security review adaptive: docs-only patch получает low-risk scope, dependency/auth/CI/deploy изменения — повышенный scope. Результат security review формулируется как no findings in reviewed scope, не как абсолютная безопасность.

Для range/branch scope Hub принимает только безопасный Git revision ref и отклоняет option-like или содержащие пробелы значения base.

Skills содержат небольшие tracked synthetic eval catalogs в `.agents/skills/*/evals/catalog.json`. Они покрывают безопасные docs-only изменения, compatibility regression, authz bypass, path traversal, secret logging и unavailable dependency scanners. Каталоги проверяются тестами как fixtures для явного Codex review; они не запускают LLM и не обещают доказательство произвольной безопасности проекта.

PUBLISHABLE возможен только после passed deterministic verification, code review и security review для одного fingerprint. Dashboard только читает состояние и не запускает LLM review автоматически.

Подробный contract и storage layout находятся в docs/operations/project-lifecycle.md.
