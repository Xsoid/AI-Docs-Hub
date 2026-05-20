---
title: GUI Dashboard
description: Локальная страница состояния AI Docs Hub.
---

GUI dashboard - локальная read-only страница состояния.

Адрес:

```text
http://localhost:4321/status/
```

## Как Работает

Страница живет в:

```text
docs-site/src/pages/status.astro
```

Данные берутся из:

```text
docs-site/src/pages/api/hub-status.json.ts
```

Endpoint запускает:

```sh
python3.11 scripts/hub-status --json
```

Страница обновляет состояние каждые 5 секунд. Кнопка `Обновить` делает тот же запрос без cache и не запускает параллельную проверку, если предыдущий запрос еще идет.

## Компоненты На Странице

- `Пульт управления` - foreground или `launchd` runtime.
- `Веб-страница` - docs-site на `localhost:4321`.
- `Настройки` - repository healthcheck.
- `Проекты` - project configs и source discovery.
- `Generated context` - `llms*.txt`, report и generated project pages.
- `Поиск по документам` - Lite RAG.
- `MkDocs` - adapter diagnostics.
- `Documentation readiness` - coverage и recommendations.
- `Связь с Codex` - MCP bridge.
- `Автообновление` - watcher heartbeat.

## Ограничение Static Build

При `astro build` endpoint `/api/hub-status.json` генерируется как static artifact на момент сборки. Для живого статуса нужен локальный runtime:

```sh
make hub-dev
```

или:

```sh
make hub-start
```

## Проверка

```sh
curl -sS http://localhost:4321/api/hub-status.json | python3.11 -m json.tool
curl -I http://localhost:4321/status/
```
