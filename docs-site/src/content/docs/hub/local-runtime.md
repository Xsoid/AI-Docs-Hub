---
title: Локальный Runtime
description: Как запустить и проверить локально активный AI Docs Hub.
---

Эта страница описывает, что означает "локально запущенный AI Docs Hub".

## Docs-Site

Отдельный запуск:

```sh
make docs-dev
```

Рекомендуемый запуск вместе с watcher:

```sh
make hub-dev
```

Persistent запуск через macOS `launchd`:

```sh
make hub-install
make hub-start
```

Ожидаемый URL:

```text
http://localhost:4321/
```

Штатный docs-site слушает HTTP. URL `https://localhost:4321/` не является ожидаемым endpoint.

Ручная проверка:

```sh
lsof -nP -iTCP:4321 -sTCP:LISTEN
curl -sS -I --max-time 3 http://localhost:4321/
```

## Healthcheck

```sh
make healthcheck
```

Проверяет структуру репозитория, project configs, поддерживаемые Python/Node runtimes, запись в `storage` и состояние Lite RAG backend.

Ограничение: `healthcheck` не доказывает, что `http://localhost:4321/` прямо сейчас поднят.

## Live Status

Основная команда:

```sh
make hub-status
```

GUI dashboard:

```text
http://localhost:4321/status/
```

Команда проверяет:

- runtime: foreground/manual runtime или `launchd`;
- docs-site: HTTP response от `http://localhost:4321/`;
- repository: результат `healthcheck`;
- projects: project configs и source discovery;
- generated: `llms*.txt`, report и generated project pages;
- rag: indexes, freshness и per-project counts;
- mkdocs: adapter state;
- docs-readiness: coverage и recommendations;
- mcp: stdio server, `tools/list` и MCP `healthcheck`;
- watcher: heartbeat от `hub-dev`.

## Статусы

- `UP`: обязательные компоненты работают, optional checks тоже в порядке.
- `DEGRADED`: обязательные компоненты работают, но optional/runtime полнота требует внимания.
- `DOWN`: один или несколько обязательных runtime-компонентов не работают.

Documentation readiness gaps являются рекомендациями и не должны сами переводить runtime в `DEGRADED`.

## Частая Авария

Симптом:

```text
Connection refused
```

Вероятные причины:

- `make docs-dev` или `make hub-dev` не запущен;
- terminal session с Astro завершилась;
- persistent `launchd` service не загружен;
- пользователь открыл `https://localhost:4321/` вместо `http://localhost:4321/`.

Восстановление:

```sh
cd <AI_DOCS_HUB_ROOT>
make hub-dev
```

или persistent:

```sh
cd <AI_DOCS_HUB_ROOT>
make hub-install
make hub-start
```

## Runtime State

`hub-dev` пишет состояние в:

```text
storage/runtime/hub-dev.status.json
```

Это runtime artifact, не source-документация.

Persistent runtime logs:

```text
storage/logs/hub-runtime.out.log
storage/logs/hub-runtime.err.log
```
