# 2026-05-15: Persistent Runtime Через `launchd`

## Кратко

Добавлен optional persistent-режим для macOS через user LaunchAgent.

## Что Изменилось

- Добавлен `scripts/hub-launchd`.
- Добавлены Makefile targets:
  - `hub-install`;
  - `hub-start`;
  - `hub-stop`;
  - `hub-restart`;
  - `hub-uninstall`;
  - `hub-launchd-status`;
  - `hub-logs`.
- `hub-status` теперь показывает компонент `runtime` и отличает foreground `hub-dev` от `launchd`-режима.
- `hub-install` генерирует plist `~/Library/LaunchAgents/local.ai-docs-hub.runtime.plist`.
- `hub-start` запускает `scripts/hub-dev` через `launchctl`.

## Поведение

LaunchAgent запускает:

```sh
python3.11 scripts/hub-dev
```

Он использует тот же foreground-supervisor, что и ручной режим. Поэтому persistent-режим не дублирует runtime-логику и не запускает docs-site/watchers разрозненными скрытыми процессами.

Логи:

```text
storage/logs/hub-runtime.out.log
storage/logs/hub-runtime.err.log
```

## Безопасность

Команды не меняют глобальный `~/.codex/config.toml`.

Установка LaunchAgent не выполняется автоматически. Ее нужно явно запустить:

```sh
make hub-install
make hub-start
```

## Проверка

Проверено:

- `python3.11 -m py_compile scripts/hub-status scripts/hub-dev scripts/hub-launchd`;
- `python3.11 scripts/hub-launchd install --dry-run`;
- `plutil -lint` для сгенерированного plist;
- `python3.11 scripts/hub-launchd status`;
- `python3.11 scripts/hub-launchd logs`;
- `python3.11 scripts/hub-status`.
- `make hub-install`;
- `make hub-start`;
- `make hub-launchd-status`;
- `make hub-logs`;
- `make hub-status` показывает `UP` при загруженном `local.ai-docs-hub.runtime`.

## Текущее Состояние

LaunchAgent установлен и запущен:

```text
~/Library/LaunchAgents/local.ai-docs-hub.runtime.plist
```

`hub-status` показывает `runtime OK` через `launchd`.

## Follow-Up

- При необходимости добавить `make hub-logs-follow` или параметризованный target для `tail -f`.
