# macOS Menu Bar

## Назначение

macOS menu bar helper добавляет маленькую иконку AI Docs Hub в верхний системный бар.

Он нужен как простой вход в GUI без запоминания адресов:

- открыть dashboard: `http://localhost:4321/status/`;
- открыть документацию: `http://localhost:4321/`;
- увидеть короткое состояние хаба;
- выйти из menu bar helper.

## Команды

Собрать приложение:

```sh
make hub-menu-build
```

Запустить иконку в верхнем баре:

```sh
make hub-menu-start
```

Проверить, запущено ли приложение:

```sh
make hub-menu-status
```

Закрыть menu bar helper:

```sh
make hub-menu-stop
```

Пересобрать и перезапустить после изменения Swift-кода или текста иконки:

```sh
make hub-menu-restart
```

## Где Лежит Приложение

Build output:

```text
build/AI Docs Hub.app
```

Этот `.app` не хранится в git. `build/` является локальным build output и игнорируется целиком.

Собрать приложение вручную:

```sh
make hub-menu-build
```

Запуск через `make hub-menu-start` тоже выполняет сборку перед стартом, если приложения еще нет или исходник был изменен.

В bundle не зашиваются абсолютные пути к checkout. При запуске приложение ищет корень хаба вверх от собственного `.app`, находит `python3.11` в переменной `AI_DOCS_HUB_PYTHON`, `PATH` или стандартных Homebrew/system путях и запускает:

```sh
python3.11 scripts/hub-status --json
```

Корень хаба определяется относительно `build/AI Docs Hub.app`, поэтому сборка не привязана к конкретной директории пользователя.

Исходники:

```text
macos/menu-bar/AIHubMenuBar.swift
scripts/hub-menubar
```

## Пункты Меню

Menu bar helper показывает:

- текущее состояние: `AI Docs Hub: работает`, `требует внимания` или `лежит`;
- `Открыть статус`;
- `Открыть документацию`;
- `Обновить состояние`;
- `Выход`.

`Выход` закрывает только menu bar helper. Runtime хаба через `launchd` при этом остается работать.

Чтобы остановить сам хаб:

```sh
make hub-stop
```

## Как Проверяется Состояние

Приложение раз в 5 секунд запускает:

```sh
python3.11 scripts/hub-status --json
```

и меняет надпись в menu bar:

- `xAI` - хаб работает;
- `xAI !` - хаб требует внимания;
- `xAI X` - хаб лежит или не удалось проверить статус.

Если локальный запуск `hub-status` не удался, helper пробует прочитать тот же статус через live API:

```text
http://localhost:4321/api/hub-status.json
```

## Ограничения

Menu bar helper не запускается автоматически после перезагрузки. Его нужно запустить явно:

```sh
make hub-menu-start
```

Runtime хаба уже может автозапускаться через `launchd`, но menu bar helper пока является отдельным пользовательским приложением.
