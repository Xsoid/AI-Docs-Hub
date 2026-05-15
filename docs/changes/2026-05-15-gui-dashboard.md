# 2026-05-15: GUI Dashboard Для Статуса Хаба

## Кратко

Добавлена локальная страница статуса AI Docs Hub:

```text
http://localhost:4321/status/
```

## Что Изменилось

- Добавлен `docs-site/src/pages/status.astro`.
- Добавлен `docs-site/src/pages/api/hub-status.json.ts`.
- В sidebar docs-site добавлена ссылка `Статус`.
- Добавлена документация `docs/operations/gui-dashboard.md`.

## Поведение

Страница показывает:

- общий статус хаба;
- состояние runtime, docs-site, repository, RAG, MCP и watcher;
- простые подсказки по следующим действиям;
- основные команды `make hub-status`, `make hub-logs`, `make hub-restart`.

Страница обновляется каждые 5 секунд.

## Ограничения

Dashboard не выполняет start/stop/restart действия из браузера. Управление runtime остается в явных терминальных командах, чтобы случайно не остановить сам сайт.

В `astro build` endpoint `/api/hub-status.json` генерируется статически. Live-статус предназначен для локального dev/runtime-режима через `hub-dev` или `launchd`.

## Проверка

Проверено:

- `curl -sS http://localhost:4321/api/hub-status.json`;
- `curl -I http://localhost:4321/status/`;
- `make hub-status`;
- `./scripts/docs-npm run build`.

