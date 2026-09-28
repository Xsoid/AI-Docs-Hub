# Project Lifecycle / Quality Gate

AI Docs Hub предоставляет локальный lifecycle для patch подключенного проекта. Hub отвечает за metadata, deterministic checks, fingerprint и gate state. Semantic code review и security review выполняются только явным Codex workflow и записываются обратно через MCP.

## Границы и переиспользование

Lifecycle использует существующие ProjectConfig, safe path/secret scan, project namespace, Codebase Memory, Skill Intelligence и ignored storage. Он не создает второй project discovery, RAG, security scanner или skill workflow.

Установленная версия Codex CLI предоставляет native non-interactive review через codex review, но отдельного non-interactive init subcommand не предоставляет. Поэтому onboarding не эмулирует TUI: он безопасно сохраняет пользовательский AGENTS.md и добавляет только узкий managed block с routing invariant. Native Codex review запускается явно оператором или агентом.

## Onboarding

Dry-run:

    python3.11 scripts/onboard-project --project name

Явная запись в подключенный проект:

    python3.11 scripts/onboard-project --project name --write
    make project-onboard PROJECT=name

Если AGENTS.md отсутствует, создается компактный bootstrap. Если файл существует, custom content сохраняется, а managed lifecycle block обновляется идемпотентно. Hub не перезаписывает файл целиком и не удаляет custom rules. Запись возвращает restart_required=true, потому что следующая Codex session должна загрузить измененный context.

Onboarding не создает tracked files в AI Docs Hub. Snapshot init хранится в ignored storage/project-lifecycle/name/init.json.

## Quality profile и verification

Quality profile строится по manifests, package scripts, Makefile targets, tests directory, CI workflow metadata и stack files. Из project scripts используются только существующие canonical entrypoints; Hub не устанавливает scanners и не добавляет команды в подключенный проект.

    python3.11 scripts/quality-profile --project name
    make quality-profile PROJECT=name
    python3.11 scripts/verify-patch --project name --scope working --json
    make verify-patch PROJECT=name SCOPE=staged

Verification всегда выполняет git diff --check и secret scan. Обнаруженные lint/typecheck/tests/build/check commands выполняются с timeout. Результат содержит только status, exit code, duration и output digest/size; stdout, source snippets и absolute project paths не сохраняются.

Статусы отдельных checks: passed, failed, error или skipped. Отсутствующий optional tool — skipped/not available, а не passed. Required failure блокирует gate.

## Fingerprint и scopes

Каждый результат относится к fingerprint, который включает project/namespace, repository identity hash, scope, base, HEAD, changed file list, staged/unstaged diff и relevant untracked bytes. Поддерживаются scopes working, staged, range и branch. Для range/branch нужен base.

Любой relevant byte change создает новый fingerprint. Старый verification или review не переносится на новый diff.
Для range/branch scope Hub принимает только безопасный Git revision ref и отклоняет option-like или содержащие пробелы значения base.

## Два независимых review

Подготовка compact diff-first контекста:

    python3.11 scripts/project-lifecycle prepare-review --project name --kind code
    python3.11 scripts/project-lifecycle prepare-review --project name --kind security

Hub отдает changed file metadata, quality check ids, adaptive security surface и явные context budgets. Полный репозиторий и source snippets не перечитываются автоматически. Codebase Memory и Docs MCP остаются отдельными scoped источниками для blast radius и contracts.

Code review и security review записываются раздельно MCP tools record_code_review и record_security_review. Каждый finding содержит severity, confidence, path/line, evidence, impact и remediation; security finding дополнительно фиксирует prerequisite, asset и validation. Security review может сказать только no findings in reviewed scope, но не абсолютную безопасность.

Skills содержат небольшие tracked synthetic eval catalogs в `.agents/skills/*/evals/catalog.json`. Они покрывают безопасные docs-only изменения, compatibility regression, authz bypass, path traversal, secret logging и unavailable dependency scanners. Каталоги проверяются тестами как fixtures для явного Codex review; они не запускают LLM и не обещают доказательство произвольной безопасности проекта.

## Gate state

    VERIFYING
    VERIFICATION_FAILED
    CODE_REVIEW_REQUIRED
    CODE_REVIEW_FAILED
    SECURITY_REVIEW_REQUIRED
    SECURITY_REVIEW_FAILED
    PUBLISHABLE

Состояние PUBLISHABLE возможно только для текущего fingerprint после passed verification, passed code review без blocker/major/critical/high findings и passed security review без critical/high findings. NO_PATCH означает, что выбранный scope чистый, и не является publishable patch.

    python3.11 scripts/pre-publish --project name --scope staged
    python3.11 scripts/review-status --project name
    make pre-publish PROJECT=name SCOPE=staged

## Storage и isolation

Local-only layout:

    storage/project-lifecycle/<project>/
      init.json
      quality-profile.json
      reviews/<fingerprint>/
        verification.json
        code-review.json
        security-review.json

Эти paths ignored. В Hub Git не попадают reports, diff/source snippets, реальные project paths или generated AGENTS content подключенных проектов.

## Git hooks

MVP не устанавливает и не переписывает hooks, core.hooksPath, Husky или pre-commit configuration. Strict local hook остается отдельной opt-in задачей: он может только проверять сохраненный gate status и freshness, но не запускает LLM.
