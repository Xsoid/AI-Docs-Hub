# Project Lifecycle / Quality Gate

Добавлен локальный lifecycle подключенного проекта:

- безопасный идемпотентный onboarding AGENTS.md с сохранением project-owned content;
- machine-readable quality profile и deterministic verify-patch;
- working/staged/range/branch patch fingerprint;
- отдельные code-review и security-review records с freshness проверкой;
- tracked synthetic review eval catalogs и regression tests для adaptive security scope, tampered verification records и blocking security findings;
- fail-closed validation для range/branch Git base refs, чтобы option-like значения не попадали в Git arguments;
- pre-publish state machine и local-only ignored storage;
- MCP tools и optional hub-status component без фонового запуска LLM;
- synthetic tests для onboarding, fingerprint, verification и stale gate.

Текущая версия Codex CLI не имеет отдельного non-interactive init subcommand, поэтому Hub не эмулирует TUI. Он реализует документированный safe equivalent; native codex review остается явным workflow.
