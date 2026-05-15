# 2026-05-15: `hub-status` И `hub-dev`

## Кратко

Добавлены первые runtime-команды, которые убирают слепую зону между "репозиторий настроен" и "хаб реально активен".

## Что Изменилось

- Добавлен `scripts/hub-status`.
- Добавлен `scripts/hub-dev`.
- Добавлены Makefile targets `hub-status` и `hub-dev`.
- `hub-status` показывает общий статус `UP`, `DEGRADED` или `DOWN`.
- `hub-dev` запускает docs-site и watcher в foreground-режиме, префиксует логи и пишет heartbeat/status file.

## Поведение

`hub-status` проверяет:

- docs-site на `http://localhost:4321/`;
- repository health;
- Lite RAG backend;
- MCP bridge;
- watcher heartbeat.

`hub-dev`:

- регенерирует project pages;
- запускает Astro docs-site на порту `4321`;
- запускает `scripts/watch-project --all`;
- пишет `storage/runtime/hub-dev.status.json`;
- останавливает дочерние процессы при `Ctrl+C` или падении одного из них.

## Проверка

Проверено:

- при остановленном docs-site `python3.11 scripts/hub-status` показывает `DOWN`;
- при запущенном `python3.11 scripts/hub-dev` команда `python3.11 scripts/hub-status` показывает `UP`;
- после `Ctrl+C` у `hub-dev` порт `4321` освобождается, watcher не остается висеть, `hub-status` снова показывает `DOWN`;
- `python3.11 -m py_compile scripts/hub-status scripts/hub-dev` проходит.

## Follow-Up

- Добавить persistent `launchd`-режим для автозапуска после перезагрузки.
- Добавить удобный просмотр runtime logs, если появится файловое логирование.
