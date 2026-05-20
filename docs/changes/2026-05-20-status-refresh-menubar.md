# 2026-05-20: Status Refresh And Menu Bar State

## Кратко

Исправлено расхождение между dashboard и macOS menu bar helper, когда страница показывала `Хаб работает`, а иконка в верхнем баре оставалась `xAI X`.

## Что Изменилось

- Menu bar helper больше не запускает `scripts/hub-status` напрямую через shebang.
- Helper сам находит `python3.11` через `AI_DOCS_HUB_PYTHON`, `PATH` и стандартные Homebrew/system пути.
- Для проверки helper передает расширенный `PATH`, чтобы `hub-status` видел Homebrew `node`, `npm` и Python-зависимости даже из GUI-процесса macOS.
- Если локальный запуск `hub-status` не удался, helper пробует прочитать live-статус через `/api/hub-status.json`.
- Кнопка `Обновить` на dashboard теперь явно показывает, что запрос идет, и защищена от параллельных refresh-запросов.

## Почему

GUI-приложение macOS может запускаться с урезанным окружением, где `/opt/homebrew/bin` не попадает в `PATH`. Из-за этого `#!/usr/bin/env python3.11` мог не находить Python, хотя сам хаб и web API работали.

## Проверка

Проверено:

```sh
make hub-status
make hub-menu-restart
./scripts/docs-npm run build
plutil -lint build/AI\ Docs\ Hub.app/Contents/Info.plist
```

## Follow-Up

- При необходимости добавить отдельный лог последней ошибки menu bar helper в `storage/logs`.
