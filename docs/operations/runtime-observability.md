# Наблюдаемость Runtime

## Проблема

У AI Docs Hub есть полезные проверки, но нет единой команды, которая отвечает на вопрос:

```text
Хаб полностью активен прямо сейчас?
```

Текущий `make healthcheck` может вернуть `ok`, когда docs-site не слушает `localhost:4321`. Это технически корректно для проверки репозитория и конфигов, но недостаточно для повседневной эксплуатации.

Тихие завершения процессов особенно проблемны: хаб выглядит настроенным, но фактически не активен.

## Цель

Хаб должен явно показывать runtime-состояние.

Пользователь должен видеть:

- поднят ли docs-site;
- может ли MCP стартовать и отдавать tools;
- существуют ли RAG-индексы и валидны ли конфиги;
- работают ли watcher-ы или их heartbeat устарел;
- запущен ли runtime вручную или через `launchd`;
- где лежит runtime state;
- почему компонент лежит.

## Реализованные Команды

### `make hub-status`

Человекочитаемый live runtime status.

Команда проверяет:

- runtime source: foreground `hub-dev` или `launchd`;
- docs-site через HTTP-проверку lightweight path `http://localhost:4321/status/`;
- repository health через `rag.health.run_healthcheck`;
- Lite RAG backend и количество индексов;
- MCP bridge через запуск `mcp/server.py`, `tools/list` и MCP `healthcheck`;
- watcher heartbeat из `storage/runtime/hub-dev.status.json`.

Пример:

```text
AI Docs Hub: DOWN

runtime     DOWN     no foreground hub-dev and launchd is not installed
docs-site   DOWN     [Errno 61] Connection refused at http://localhost:4321/status/
repository  OK       healthcheck ok
rag         OK       lite-json-bm25, 3 indexes
mcp         OK       10 tools available
watcher     DOWN     no heartbeat at storage/runtime/hub-dev.status.json

runtime:
storage/runtime/hub-dev.status.json

next:
- start foreground runtime: make hub-dev
- install persistent runtime: make hub-install && make hub-start
- watcher heartbeat is produced by make hub-dev
```

Точные exit codes дает прямой вызов:

```sh
python3.11 scripts/hub-status
```

Exit codes скрипта:

- `0`: все runtime-проверки проходят, статус `UP`;
- `1`: одна или несколько обязательных runtime-проверок не проходят, статус `DOWN`;
- `2`: optional или degraded компонент требует внимания.

`make hub-status` является удобной оберткой. При non-zero статусе `make` дополнительно печатает свою строку ошибки.

### `make hub-dev`

Foreground supervisor для локальной разработки.

Ответственность:

- запускать docs-site и watcher вместе;
- префиксовать логи по компонентам;
- явно останавливаться, когда обязательный child process завершился;
- писать runtime heartbeat/status files;
- избегать скрытых background-процессов.

Текущее поведение:

- перед запуском выполняет `scripts/generate-project-pages`;
- запускает docs-site через `scripts/docs-npm run dev -- --host 0.0.0.0 --port 4321`;
- запускает watcher через `scripts/watch-project --all`;
- запускает local fix action server через `scripts/fix-server` на `127.0.0.1:4322`;
- префиксует stdout дочерних процессов как `[docs]` и `[watch]`;
- проверяет, что docs-site начал слушать TCP на `localhost:4321`;
- пишет `storage/runtime/hub-dev.status.json`;
- при `Ctrl+C`, `SIGTERM` или падении дочернего процесса останавливает все дочерние процессы.

Дополнительные опции:

```sh
python3.11 scripts/hub-dev --no-watch
python3.11 scripts/hub-dev --host 127.0.0.1 --port 4321
```

`--no-watch` полезен для отладки docs-site, но `hub-status` в этом режиме не будет считать runtime полностью `UP`, потому что watcher heartbeat отсутствует.

## Persistent Runtime Commands

### `make hub-start`

Запускает persistent runtime через host supervisor.

На macOS используется user LaunchAgent:

- label: `local.ai-docs-hub.runtime`;
- plist: `~/Library/LaunchAgents/local.ai-docs-hub.runtime.plist`;
- command: `python3.11 scripts/hub-dev`.

Перед первым запуском нужен:

```sh
make hub-install
```

`make hub-install` только создает plist. MCP-подключения для Codex настраиваются отдельной точечной правкой глобального Codex config.

### `make hub-stop`

Останавливает persistent service через `launchctl bootout`.

### `make hub-restart`

Останавливает и снова запускает persistent service.

### `make hub-launchd-status`

Показывает, установлен ли plist и загружен ли service в `launchd`.

### `make hub-uninstall`

Останавливает service и удаляет plist.

### `make hub-logs`

Показывает последние строки:

```text
storage/logs/hub-runtime.out.log
storage/logs/hub-runtime.err.log
```

## Runtime State File

Foreground supervisor пишет:

```text
storage/runtime/hub-dev.status.json
```

Текущая структура:

```json
{
  "status": "running",
  "pid": 12345,
  "checked_at": "2026-05-15T08:00:00Z",
  "message": "running",
  "children": {
    "docs-site": {
      "pid": 12346,
      "status": "running",
      "url": "http://localhost:4321/",
      "health_url": "http://localhost:4321/status/",
      "http": "TCP localhost:4321"
    },
    "watcher": {
      "pid": 12347,
      "status": "running"
    },
    "fix-server": {
      "pid": 12348,
      "status": "running",
      "url": "http://127.0.0.1:4322/"
    }
  }
}
```

`storage/runtime/` - runtime state, а не source-документация.

Persistent runtime пишет stdout/stderr через launchd в:

```text
storage/logs/
```

Логи являются runtime-артефактами и не коммитятся.

## Acceptance Criteria Для Текущего Этапа

Текущий этап observability считается завершенным, когда:

- `make hub-status` явно отличает repository health от live runtime state;
- недоступный `localhost:4321` показывается как docs-site down;
- вывод команды содержит actionable next steps или путь к runtime state;
- foreground dev mode не скрывает завершения child processes;
- persistent mode имеет явные install/start/stop/restart/status/logs/uninstall commands;
- документация в `/docs` обновлена под фактическое поведение.

## Текущий Статус

`hub-status`, `hub-dev` и persistent `launchd` commands реализованы.

Persistent service не устанавливается автоматически. Для включения автозапуска нужно явно выполнить `make hub-install` и `make hub-start`.

GUI dashboard реализован по адресу:

```text
http://localhost:4321/status/
```

Он использует `/api/hub-status.json`, который вызывает `scripts/hub-status --json --docs-site-self-ok`, чтобы не делать рекурсивный HTTP-call в тот же Astro process.

Dashboard может запускать allowlisted fix actions через `http://127.0.0.1:4322/apply-fix`. Runtime actions ограничены `launchd` supervisor, а RAG action `rag.reindex` работает только в одном project namespace.
