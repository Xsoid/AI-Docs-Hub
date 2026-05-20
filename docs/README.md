# Документация AI Docs Hub

Эта директория является source-документацией самого AI Docs Hub.

Документация конкретных проектов по-прежнему хранится внутри этих проектов. Хаб может читать подключенные проекты и строить derived-представления, индексы и `llms*.txt`, но не должен становиться источником правды для приватных знаний другого проекта.

## Назначение

В `/docs` документируются:

- архитектура хаба и runtime-поведение;
- эксплуатационные runbook-и;
- проектные решения и tradeoff-ы;
- стандарты для будущих изменений хаба;
- заметки об осмысленных изменениях.

Не используйте `/docs` для:

- generated-артефактов;
- RAG-индексов;
- скопированной документации подключенных проектов;
- секретов, credentials, tokens, cookies, sessions, dumps, private keys или secret-looking значений.

## Структура

```text
docs/
  architecture/     # устройство системы, слои, границы, data flow
  operations/       # runbook-и, проверки статуса, локальный runtime
  decisions/        # ADR-style решения
  standards/        # правила сопровождения хаба
  changes/          # человекочитаемые заметки об изменениях
```

## Правило Документирования

Каждая значимая доработка AI Docs Hub должна обновлять `/docs` в том же change set.

Минимум:

- обновить релевантную страницу архитектуры, эксплуатации или стандартов;
- добавить или обновить decision record, если меняется поведение, зона ответственности или runtime-модель;
- добавить заметку в `docs/changes/`, если изменение влияет на использование, эксплуатацию или отладку хаба.

Если код и документация конфликтуют, нужно явно сообщить о конфликте с путями к обоим источникам, а не скрывать расхождение.

## Язык Документации

Основной язык документации AI Docs Hub в `/docs` - русский.

Технические термины, имена команд, форматы файлов и общепринятые англоязычные понятия можно оставлять на английском, если перевод ухудшает точность.

## Текущее Runtime-Состояние

На 2026-05-15 у хаба есть независимые локальные слои:

- docs-site: Astro dev server, обычно запускается через `make docs-dev` или через общий foreground runtime `make hub-dev`;
- Lite RAG: локальные JSON/BM25-индексы в `storage/index`;
- watcher: foreground polling process, запускается через `make watch`, `make watch-all` или вместе с docs-site через `make hub-dev`;
- MCP bridge: stdio-сервер, запускается клиентами или через `make mcp-dev`;
- healthcheck: проверка репозитория, конфигов и runtime-prerequisites, но не доказательство, что docs-site прямо сейчас слушает порт;
- hub-status: live runtime-проверка, которая показывает `UP`, `DEGRADED` или `DOWN`;
- launchd runtime: optional persistent-режим для macOS, управляется через `make hub-install`, `make hub-start`, `make hub-stop`, `make hub-restart`, `make hub-logs`.
- GUI dashboard: локальная страница `http://localhost:4321/status/` для понятного просмотра состояния хаба.
- macOS menu bar: иконка в верхнем системном баре, запускается через `make hub-menu-start`.

Штатный docs-site слушает `http://localhost:4321/`; `https://localhost:4321/` не является default endpoint.

См. [Локальный Runtime](operations/local-runtime.md), [Наблюдаемость Runtime](operations/runtime-observability.md) и [Справочник Команд](operations/command-reference.md).
