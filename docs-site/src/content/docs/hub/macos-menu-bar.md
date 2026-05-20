---
title: macOS Menu Bar
description: Optional Swift/AppKit helper для быстрого доступа к status и docs.
---

macOS menu bar helper добавляет маленькую иконку AI Docs Hub в верхний системный бар.

Он нужен как быстрый вход в GUI:

- открыть dashboard: `http://localhost:4321/status/`;
- открыть документацию: `http://localhost:4321/`;
- увидеть короткий runtime status;
- выйти из helper.

## Команды

```sh
make hub-menu-build
make hub-menu-start
make hub-menu-status
make hub-menu-stop
make hub-menu-restart
```

Build output:

```text
build/AI Docs Hub.app
```

`build/` не коммитится.

## Source Files

```text
macos/menu-bar/AIHubMenuBar.swift
scripts/hub-menubar
```

Bundle не зашивает абсолютный путь к checkout. Helper ищет root хаба относительно `build/AI Docs Hub.app`, находит `python3.11` через `AI_DOCS_HUB_PYTHON`, `PATH` или стандартные Homebrew/system paths и запускает:

```sh
python3.11 scripts/hub-status --json
```

## Пункты Меню

- текущее состояние;
- `Открыть статус`;
- `Открыть документацию`;
- `Обновить состояние`;
- `Выход`.

`Выход` закрывает только menu bar helper. Runtime хаба через `launchd` при этом остается работать.

## Ограничение

Menu bar helper не запускается автоматически после перезагрузки. Persistent runtime может автозапускаться через `launchd`, но helper пока запускается отдельно.
