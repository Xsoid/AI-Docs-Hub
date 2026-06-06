# Runtime Status Standard

AI Docs Hub отделяет repository health от live runtime state.

## Repository Health

```sh
make healthcheck
```

Проверяет:

- required paths;
- Python 3.11;
- Node.js 22/npm 10;
- storage writability;
- project configs;
- Lite RAG backend;
- docs-site package presence.

Это не доказывает, что docs-site слушает порт.

## Live Runtime

```sh
make hub-status
```

Проверяет live components:

- runtime;
- docs-site;
- repository;
- projects;
- generated;
- rag;
- mkdocs;
- docs-readiness;
- mcp;
- watcher.

`hub-dev` также запускает `scripts/fix-server` на `127.0.0.1:4322` для dashboard fix actions. Это runtime child process, а не source-of-truth.

CLI `hub-status` проверяет docs-site HTTP через lightweight dashboard path `http://localhost:4321/status/`; для probe используется system `curl`, если он доступен. Dashboard API не делает recursive HTTP-call в тот же Astro process и запускает `hub-status` с `--docs-site-self-ok`.

Статусы:

- `UP`: все checks ok;
- `DEGRADED`: required checks ok, но optional check требует внимания;
- `DOWN`: required check failed.

## URLs

Docs-site expected URL:

```text
http://localhost:4321/
```

Status dashboard:

```text
http://localhost:4321/status/
```

HTTPS на `localhost:4321` не является default runtime endpoint.
