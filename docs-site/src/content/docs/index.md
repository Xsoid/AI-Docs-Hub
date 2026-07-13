---
title: AI Docs Hub
description: Local documentation hub for docs-as-code, llms.txt, RAG, and MCP access.
---

AI Docs Hub - локальный инфраструктурный хаб для проектной документации, generated-контекста, Lite RAG-индексов и MCP-доступа.

Главное правило: документация конкретного проекта остается внутри этого проекта. Хаб хранит конфиги подключения, локальные индексы, generated-файлы, шаблоны, runtime-инструменты и надпроектную документацию.

## Что Делает Хаб

- Читает разрешенные Markdown/source-файлы из `configs/projects/*.yaml`.
- Строит project-scoped Lite JSON/BM25 индексы в `storage/index`.
- Генерирует `llms.txt`, `llms-full.txt` и `llms-small.txt`.
- Генерирует обзорные страницы подключенных проектов для docs-site.
- Отдает project-scoped MCP tools для Codex и других локальных агентов.
- Подключает optional project-scoped [Codebase Memory](/hub/codebase-memory/) MCP для поиска symbols, calls, dependencies, routes и blast radius.
- Показывает live runtime/status dashboard на `/status/`.
- Проверяет documentation readiness и может dry-run scaffold недостающих проектных docs.

## Что Не Делает Хаб

- Не становится source of truth для документации подключенных проектов.
- Не смешивает namespace разных проектов без явного запроса.
- Не индексирует `.env`, ключи, токены, cookies, sessions, dumps или secret-looking files.
- Не редактирует подключенные проекты по умолчанию.
- Не требует Docker, RAGFlow, cloud vector DB или внешних LLM API для штатной работы.

## Быстрый Старт

```sh
make setup
make hub-dev
```

Открыть сайт:

```text
http://localhost:4321/
```

Проверить live-состояние:

```sh
make hub-status
```

Первая точка для чтения - [Обзор](/hub/overview/), затем [Архитектура](/hub/architecture/), [Codebase Memory](/hub/codebase-memory/) и [Справочник команд](/hub/command-reference/).
