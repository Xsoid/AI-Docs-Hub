# 2026-05-15: macOS Menu Bar Helper

## Кратко

Добавлено native macOS menu bar приложение для быстрого доступа к AI Docs Hub.

## Что Изменилось

- Добавлен Swift source `macos/menu-bar/AIHubMenuBar.swift`.
- Добавлен управляющий скрипт `scripts/hub-menubar`.
- `build/AI Docs Hub.app` считается локальным build output и не хранится в git.
- Добавлены Makefile targets:
  - `hub-menu-build`;
  - `hub-menu-start`;
  - `hub-menu-stop`;
  - `hub-menu-restart`;
  - `hub-menu-status`.
- Добавлена документация `docs/operations/macos-menu-bar.md`.

## Поведение

Иконка в верхнем баре показывает короткий статус:

- `xAI`;
- `xAI !`;
- `xAI X`.

Меню содержит:

- `Открыть статус`;
- `Открыть документацию`;
- `Обновить состояние`;
- `Выход`.

`Выход` закрывает только menu bar helper. Persistent runtime хаба продолжает работать.

## Проверка

Проверено:

- `make hub-menu-build`;
- `plutil -lint build/AI Docs Hub.app/Contents/Info.plist`;
- `make hub-menu-start`;
- `make hub-menu-status`;
- `make hub-status`.

## Исправления

- `scripts/hub-menubar stop/status` теперь ищет только реально запущенный menu bar executable и не принимает команду `swiftc -o .../AI Docs Hub Menu` за запущенное приложение.
- Bundle больше не содержит абсолютные `AIHubRoot` и `AIHubPython`; приложение само находит корень хаба относительно `.app` и запускает `scripts/hub-status --json`.
- После изменения Swift-кода или текста в верхнем баре нужно использовать `make hub-menu-restart`, чтобы остановить старый процесс, пересобрать binary и запустить новый.
- Документация явно фиксирует, что `.app` собирается локально через `make hub-menu-build`, а `build/` остается ignored.

## Follow-Up

- При необходимости добавить отдельный optional login item для автозапуска menu bar helper после входа в macOS.
