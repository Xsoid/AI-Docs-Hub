# Codebase Memory Sidecar

Date: 2026-07-11

AI Docs Hub получил optional Codebase Memory integration для project-scoped анализа исходного кода.

Изменение добавляет hub-managed install/status/index commands, explicit-only wrapper с `persistence=false`, обязательный `.cbmignore` security gate, ignored binary/SQLite cache и optional status component.

Lite RAG, docs-as-code и Markdown ADR остаются source-of-truth слоями документации. Codebase Memory используется только для symbols, calls, dependencies и impact analysis.

Дополнительно исправлены две найденные при проверке проблемы: dashboard теперь включает `codebase-memory` в явный render order, а documentation lint больше не считает RAG chunks одного длинного Markdown-раздела duplicate headings.

Dashboard также получил project connection matrix и allowlisted actions для Docs RAG, Generated context и Codebase Memory. `security_skipped` RAG rows теперь показывают кнопку безопасной актуализации без обхода secret scan.

Fix workflow визуализирует весь lifecycle локальной job: запуск, очередь, выполнение, повторные polls, завершение или ошибку. Панель операции сохраняет job id, elapsed time и итог после автоматического refresh статуса.

Code graph onboarding теперь считается полным только при наличии index, отдельного project-scoped MCP и managed routing rules в project `AGENTS.md`. Existing graph-only подключения автоматически мигрированы через идемпотентный action; Codex требует перезапуска для загрузки новых MCP servers.
