# Обзор Архитектуры

AI Docs Hub - локальный инфраструктурный репозиторий для документации, generated-контекста, Lite RAG-индексов и MCP-доступа.

Хаб намеренно разделен на независимые слои. Это сохраняет изоляцию проектной документации и делает generated-артефакты воспроизводимыми.

## Карта Стеков

AI Docs Hub - это локальная multi-stack система. У каждого стека должна быть понятная зона ответственности:

- Python 3.11: operational scripts, загрузка project configs, Lite RAG, MCP stdio server, healthcheck, источник данных для status API, allowlisted fix actions, watcher, documentation scaffold, secret scanning, generated project pages и генерация `llms*.txt`;
- Node.js 22 LTS и npm 10: runtime и build pipeline для docs-site;
- Astro 6 и Starlight: сайт документации, shell страницы `/status/`, status/fix API endpoints, навигация, сборка search index и рендеринг контента из `docs-site/src/content/docs/`;
- Markdown docs-as-code: source-документация хаба в `docs/`, source-страницы docs-site в `docs-site/src/content/docs/` и документация подключенных проектов внутри самих проектов;
- YAML project config: `configs/projects/*.yaml` задают project root, namespace, source include/exclude rules, agent rules и docs backend mode;
- MkDocs adapter: read-only structural discovery для проектов с `mkdocs.yml` или `mkdocs.yaml`; adapter не запускает MkDocs plugins, hooks, Python code или Markdown extensions;
- Lite JSON/BM25 RAG: локальная индексация и поиск по разрешенной документации проектов, хранение в `storage/index`;
- MCP stdio bridge: `mcp/server.py` отдает project-scoped tools для Codex и других MCP clients через JSON-RPC stdio;
- optional Codebase Memory sidecar: отдельный MCP/CLI строит project-scoped SQLite graph исходного кода для symbols, calls, dependencies и impact analysis; cache хранится в ignored `storage/codebase-memory`;
- local runtime: `scripts/hub-dev` супервизирует docs-site, watcher и local fix action server в foreground; macOS `launchd` может запускать тот же supervisor persistently;
- macOS menu bar app: optional Swift/AppKit wrapper, который собирается через `scripts/hub-menubar`; это operational convenience, а не source of truth;
- generated artifacts: `storage/generated`, `docs-site/public/llms*.txt`, `docs-site/src/content/docs/projects/*`, runtime heartbeats, logs и indexes являются derived-артефактами.

Docker, RAGFlow, external vector databases, cloud search и remote LLM APIs не входят в default working stack хаба.

Codebase Memory не является default dependency: Lite RAG и Markdown ADR остаются независимыми source-of-truth слоями, а отсутствие sidecar не останавливает Hub. Operational model, onboarding и список разрешенных MCP tools описаны в `docs/operations/codebase-memory.md`.

## Слои

### Docs-As-Code

Подключенные проекты хранят собственную source-документацию в своих репозиториях. Хаб читает настроенные файлы через `configs/projects/*.yaml`.

Собственная документация хаба живет в `/docs`.

Project config поддерживает слой source discovery. По умолчанию `docs_backend: auto` читает обычные `sources`/`include`/`exclude`, а если в корне проекта найден `mkdocs.yml` или `mkdocs.yaml`, дополнительно применяет безопасную часть MkDocs-конфига:

- `docs_dir` добавляет Markdown-файлы из каталога документации;
- `site_dir`, `exclude_docs` и `draft_docs` преобразуются в exclude-паттерны;
- `nav` читается как справочная структура, но не является единственным источником файлов.

MkDocs adapter не запускает `mkdocs build`, `plugins`, `hooks` или Markdown extensions. Если `docs_backend: mkdocs` задан явно, но `mkdocs.yml` отсутствует, хаб сообщает warning и продолжает использовать обычные include-паттерны.

### Пути И Переносимость

В source-файлах хаба не должно быть hard-coded абсолютных путей к checkout, соседним проектам, Python runtime или пользовательским директориям.

Для путей используются:

- вычисление от корня репозитория;
- `${AI_DOCS_PROJECTS_ROOT}` для подключенных проектов рядом с хабом;
- placeholder-ы в шаблонах: `<AI_DOCS_HUB_ROOT>`, `<EXTERNAL_PROJECT_ROOT>`, `__AI_DOCS_HUB_ROOT__`, `__PYTHON3_11__`;
- host-specific абсолютные пути только в runtime-generated файлах вне source-of-truth, если этого требует macOS `launchd` или внешний клиент.

### Docs-Site

`docs-site/` - Astro Starlight сайт для просмотра документации хаба и generated overview-страниц проектов.

Текущее поведение:

- `make docs-dev` регенерирует страницы проектов и запускает Astro в foreground-режиме;
- локальный URL по умолчанию: `http://localhost:4321/`;
- `/status/` показывает runtime-состояние хаба и project-scoped diagnostics там, где это имеет смысл: project config/source discovery, generated project pages, RAG indexes, MkDocs adapter, documentation readiness и scaffold availability;
- `/api/apply-fix.json` запускает только allowlisted fix actions через `scripts/apply-fix`;
- процесс docs-site пока не супервизируется самим хабом.

### Lite RAG

RAG backend по умолчанию - локальное JSON/BM25-хранилище в `storage/index`.

Индексация должна оставаться project-scoped. Secret-looking файлы и явно исключенные пути нельзя индексировать.

Перед индексацией строится effective source plan: ручные include/exclude правила объединяются с безопасно прочитанными MkDocs-правилами, затем применяется exclude filtering и secret scan.

Status page показывает RAG backend, количество source-файлов, indexed documents, chunks, путь к индексу, время индексации, newest source timestamp и freshness по каждому проекту. Stale index является operational warning, потому что поиск может отставать от docs-as-code.

### Documentation Scaffold

Хаб может инициировать создание недостающих рекомендованных файлов документации в подключенном проекте через `scripts/scaffold-project-docs`.

Это отдельный workflow от индексации:

- default mode - dry-run, который показывает план файлов;
- запись в проект требует `--write`, `make scaffold-docs-write` или MCP `scaffold_project_docs` с `confirm=true`;
- команда создает только отсутствующие файлы или заполняет пустые recommended-файлы;
- existing non-empty files не перезаписываются;
- содержимое берется из `templates/project-docs/` и встроенных starter-шаблонов.
- отчет показывает documentation coverage до и после выполнения.

Так Хаб остается read-only по умолчанию, но может явно помогать довести проект до рекомендуемой docs-структуры.

### Generated-Контекст

`scripts/generate-llms` создает `llms.txt`, `llms-full.txt` и `llms-small.txt`.

Эти файлы являются derived-артефактами. Они не являются hand-authored source-документацией.

### MCP Bridge

`mcp/server.py` - stdio MCP server. Он предоставляет scoped-инструменты для списка проектов, чтения документации, поиска по индексам, индексации проектов, lint-проверки документации и healthcheck.

Так как сервер работает через stdio, MCP обычно запускается клиентом, который его использует. По умолчанию это не long-running HTTP service.

### Watcher-Ы

`scripts/watch-project` может следить за одним настроенным проектом или за всеми валидными проектами и переиндексировать их при изменении source-документации.

Watcher работает в foreground-режиме через `make watch`, `make watch-all` или как дочерний процесс `make hub-dev`.

### Runtime Supervisor

`scripts/hub-dev` - foreground supervisor для локального runtime. Он запускает docs-site, watcher и `scripts/fix-server` вместе, префиксует логи, пишет heartbeat/status file в `storage/runtime/hub-dev.status.json` и останавливает дочерние процессы при завершении.

На macOS optional persistent-режим строится через `launchd`: `scripts/hub-launchd` устанавливает user LaunchAgent `local.ai-docs-hub.runtime`, который запускает тот же `scripts/hub-dev`.

Persistent runtime отделен от глобального Codex config; MCP-подключения настраиваются отдельной точечной правкой `~/.codex/config.toml`.

### Fix Actions

`scripts/fix-server` обслуживает локальные dashboard кнопки на `127.0.0.1:4322` и вызывает `scripts/apply-fix`.

`scripts/apply-fix` - allowlisted executor для operational fixes, которые запускаются из dashboard или CLI. Он не принимает произвольные shell-команды.

Project-scoped fix actions, например `rag.reindex`, используют обычные project configs, namespace isolation, exclude rules и secret scan. Runtime fix actions ограничены управлением описанным `launchd` supervisor.

## Source Of Truth

- документация хаба: `/docs`;
- документация подключенных проектов: каждый подключенный проект;
- страницы docs-site: web-представление и generated project views;
- RAG-индексы и `llms*.txt`: derived-артефакты.
