---
title: Наблюдаемость Runtime
description: Как hub-status и dashboard показывают live-состояние хаба.
---

`make healthcheck` отвечает на вопрос "репозиторий и prerequisites пригодны?", но не отвечает на вопрос "хаб прямо сейчас активен?". Для live runtime используется отдельный слой observability.

## `make hub-status`

```sh
make hub-status
```

Команда проверяет:

- runtime source: foreground `hub-dev` или macOS `launchd`;
- docs-site через HTTP-проверку lightweight path `http://localhost:4321/status/`;
- repository health через `rag.health.run_healthcheck`;
- project configs и source discovery;
- generated context и generated project pages;
- Lite RAG backend, per-project indexes и freshness;
- MkDocs adapter state;
- documentation readiness coverage;
- MCP bridge через `initialize`, `tools/list` и MCP `healthcheck`;
- watcher heartbeat из `storage/runtime/hub-dev.status.json`.

Прямой вызов возвращает точные exit codes:

```sh
python3.11 scripts/hub-status
```

- `0`: `UP`;
- `1`: `DOWN`;
- `2`: `DEGRADED`.

JSON:

```sh
python3.11 scripts/hub-status --json
```

## `make hub-dev`

Foreground supervisor:

- выполняет `scripts/generate-project-pages` перед стартом;
- запускает docs-site через `scripts/docs-npm run dev -- --host 0.0.0.0 --port 4321`;
- запускает watcher через `scripts/watch-project --all`;
- запускает local fix action server через `scripts/fix-server` на `127.0.0.1:4322`;
- префиксует logs как `[docs]` и `[watch]`;
- проверяет, что docs-site начал слушать TCP на `localhost:4321`;
- пишет heartbeat/status file;
- останавливает дочерние процессы при `Ctrl+C`, `SIGTERM` или падении child process.

Полезные options:

```sh
python3.11 scripts/hub-dev --no-watch
python3.11 scripts/hub-dev --host 127.0.0.1 --port 4321
```

`--no-watch` полезен для отладки сайта, но `hub-status` не будет считать runtime полностью `UP`, потому что watcher heartbeat отсутствует.

## Persistent Runtime

macOS commands:

```sh
make hub-install
make hub-start
make hub-stop
make hub-restart
make hub-launchd-status
make hub-logs
make hub-uninstall
```

LaunchAgent label:

```text
local.ai-docs-hub.runtime
```

Plist:

```text
~/Library/LaunchAgents/local.ai-docs-hub.runtime.plist
```

Persistent service не устанавливается автоматически.

## Dashboard

`/status/` вызывает `/api/hub-status.json`, а endpoint запускает:

```sh
python3.11 scripts/hub-status --json --docs-site-self-ok
```

Dashboard может запускать allowlisted fix actions через `http://127.0.0.1:4322/apply-fix`. Runtime actions ограничены `launchd` supervisor, а RAG action `rag.reindex` работает только в одном project namespace.
