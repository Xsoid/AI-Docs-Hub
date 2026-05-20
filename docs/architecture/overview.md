# Обзор Архитектуры

AI Docs Hub - локальный инфраструктурный репозиторий для документации, generated-контекста, Lite RAG-индексов и MCP-доступа.

Хаб намеренно разделен на независимые слои. Это сохраняет изоляцию проектной документации и делает generated-артефакты воспроизводимыми.

## Слои

### Docs-As-Code

Подключенные проекты хранят собственную source-документацию в своих репозиториях. Хаб читает настроенные файлы через `configs/projects/*.yaml`.

Собственная документация хаба живет в `/docs`.

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
- процесс docs-site пока не супервизируется самим хабом.

### Lite RAG

RAG backend по умолчанию - локальное JSON/BM25-хранилище в `storage/index`.

Индексация должна оставаться project-scoped. Secret-looking файлы и явно исключенные пути нельзя индексировать.

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

`scripts/hub-dev` - foreground supervisor для локального runtime. Он запускает docs-site и watcher вместе, префиксует логи, пишет heartbeat/status file в `storage/runtime/hub-dev.status.json` и останавливает дочерние процессы при завершении.

На macOS optional persistent-режим строится через `launchd`: `scripts/hub-launchd` устанавливает user LaunchAgent `local.ai-docs-hub.runtime`, который запускает тот же `scripts/hub-dev`.

Persistent runtime отделен от глобального Codex config; MCP-подключения настраиваются отдельной точечной правкой `~/.codex/config.toml`.

## Source Of Truth

- документация хаба: `/docs`;
- документация подключенных проектов: каждый подключенный проект;
- страницы docs-site: web-представление и generated project views;
- RAG-индексы и `llms*.txt`: derived-артефакты.
