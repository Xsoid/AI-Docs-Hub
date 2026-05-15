# Локальный Runtime

Эта страница описывает, что сегодня означает "локально запущенный AI Docs Hub".

## Компоненты

### Docs-Site

Отдельный запуск:

```sh
make docs-dev
```

Рекомендуемый запуск вместе с watcher-ом:

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

Docs-site активен только пока работает Astro dev process. Если терминал или родительская сессия завершается, сайт может остановиться.

`make hub-dev` запускает docs-site в foreground-режиме, префиксует его логи как `[docs]` и останавливает дочерние процессы при `Ctrl+C`.

`make hub-start` запускает тот же `hub-dev`, но через user LaunchAgent `local.ai-docs-hub.runtime`.

Ручная проверка:

```sh
lsof -nP -iTCP:4321 -sTCP:LISTEN
curl -sS -I --max-time 3 http://localhost:4321/
```

Ожидаемый HTTP-результат:

```text
HTTP/1.1 200 OK
```

### Healthcheck

Запуск:

```sh
make healthcheck
```

Проверяет структуру репозитория, project configs, поддерживаемые Python и Node runtimes, доступность записи в storage и состояние RAG backend.

Важное ограничение: `make healthcheck` сейчас не доказывает, что `http://localhost:4321/` поднят.

### MCP Bridge

Запуск теста:

```sh
make mcp-test
```

Команда запускает stdio MCP server, инициализирует его, получает список tools, вызывает `healthcheck` и завершает работу.

MCP bridge обычно запускается клиентом. Сейчас это не persistent HTTP daemon.

### Watcher

Следить за одним проектом:

```sh
make watch PROJECT=example-project
```

Следить за всеми валидными проектами:

```sh
make watch-all
```

Watcher работает в foreground-режиме, пишет логи в stdout и останавливается по `Ctrl+C` или при завершении родительской сессии, если он не установлен через supervisor.

`make hub-dev` запускает watcher через `scripts/watch-project --all`, префиксует его логи как `[watch]` и пишет heartbeat в `storage/runtime/hub-dev.status.json`.

## Проверка "Жив Ли Хаб?"

Основная команда:

```sh
make hub-status
```

GUI dashboard:

```text
http://localhost:4321/status/
```

macOS menu bar helper:

```sh
make hub-menu-start
```

Или напрямую, если нужны точные exit codes без поведения `make`:

```sh
python3.11 scripts/hub-status
```

Команда проверяет:

- runtime: foreground/manual runtime или `launchd` service;
- docs-site: HTTP-ответ от `http://localhost:4321/`;
- repository: результат `healthcheck`;
- rag: наличие Lite RAG backend и количество индексов;
- mcp: старт stdio MCP server, `tools/list` и MCP healthcheck;
- watcher: свежий heartbeat от `make hub-dev`.

Статусы:

- `UP`: обязательные компоненты работают, watcher heartbeat свежий;
- `DEGRADED`: обязательные компоненты работают, но optional/runtime полнота не достигнута, например нет watcher heartbeat;
- `DOWN`: один или несколько обязательных runtime-компонентов не работают.

Ручные проверки остаются полезны для диагностики:

```sh
make healthcheck
make mcp-test
lsof -nP -iTCP:4321 -sTCP:LISTEN
curl -sS -I --max-time 3 http://localhost:4321/
```

Интерпретация:

- healthcheck ok: репозиторий и prerequisites пригодны к работе;
- MCP test ok: MCP server может стартовать и отдавать tools;
- порт 4321 слушается и HTTP 200: docs-site сейчас поднят;
- порт 4321 отсутствует: docs-site лежит, даже если healthcheck ok.

## Частая Авария: `localhost:4321` Недоступен

Симптомы:

```text
Connection refused
```

Вероятная причина:

- `make docs-dev` не запущен;
- терминал или сессия, владевшая Astro, завершилась;
- Astro упал до того, как начал слушать порт.

Восстановление через общий foreground runtime:

```sh
cd <AI_DOCS_HUB_ROOT>
make hub-dev
```

Восстановление через persistent runtime:

```sh
cd <AI_DOCS_HUB_ROOT>
make hub-install
make hub-start
```

Или отдельный запуск docs-site:

```sh
cd <AI_DOCS_HUB_ROOT>
make docs-dev
```

Затем проверить:

```sh
curl -sS -I --max-time 3 http://localhost:4321/
```

## Runtime State

`make hub-dev` пишет текущее состояние в:

```text
storage/runtime/hub-dev.status.json
```

Этот файл не является source-документацией и не коммитится. Он нужен для `hub-status`, чтобы отличать активный watcher от остановленного или устаревшего runtime.

## Persistent Runtime

На macOS persistent runtime управляется командами:

```sh
make hub-install
make hub-start
make hub-stop
make hub-restart
make hub-launchd-status
make hub-logs
make hub-uninstall
```

Menu bar helper управляется отдельно:

```sh
make hub-menu-start
make hub-menu-status
make hub-menu-stop
```

`make hub-install` создает:

```text
~/Library/LaunchAgents/local.ai-docs-hub.runtime.plist
```

LaunchAgent запускает:

```sh
python3.11 scripts/hub-dev
```

Логи:

```text
storage/logs/hub-runtime.out.log
storage/logs/hub-runtime.err.log
```

Установка LaunchAgent не выполняется автоматически при обычной работе с репозиторием. Ее нужно запускать явно.
