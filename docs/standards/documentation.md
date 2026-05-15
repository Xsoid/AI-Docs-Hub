# Стандарт Документации

Документация является частью definition of done для изменений AI Docs Hub.

## Правило

Каждое значимое изменение хаба должно обновлять `/docs`.

Это включает изменения в:

- RAG behavior;
- MCP tools или protocol behavior;
- docs-site behavior;
- правилах индексации;
- generated context files;
- runtime commands;
- launch или supervision behavior;
- project config behavior;
- operational workflows.

## Язык

Основной язык документации в `/docs` - русский.

Можно оставлять английскими:

- имена команд, файлов, директорий, API и протоколов;
- термины, где русский перевод хуже передает смысл;
- quoted output команд;
- machine-readable примеры.

Если документ добавляется на английском, его нужно перевести до завершения работы.

## Где Документировать

Используйте:

- `docs/architecture/` для system design, границ, слоев и data flow;
- `docs/operations/` для runbook-ов, проверок статуса, логов, startup, shutdown и recovery;
- `docs/decisions/` для ADR-style решений;
- `docs/standards/` для правил, которым должны следовать будущие агенты и maintainers;
- `docs/changes/` для человекочитаемых заметок о значимых изменениях.

## Change Notes

Добавляйте файл в `docs/changes/`, когда изменение влияет на использование, эксплуатацию, отладку или расширение хаба.

Change note должен содержать:

- дату;
- краткое описание;
- измененное поведение;
- выполненную проверку;
- follow-up, если он есть.

## Обработка Конфликтов

Если документация и код расходятся, нельзя молча выбирать один источник.

Нужно указать оба пути и сам конфликт. Затем обновить source-документацию или код в рамках исправления.

## Generated Files

Не редактируйте derived-артефакты вручную как source-документацию.

Примеры:

- `storage/index/*.json`;
- `storage/generated/*`;
- `docs-site/public/llms.txt`;
- `docs-site/public/llms-full.txt`;
- `docs-site/public/llms-small.txt`.

## Абсолютные Пути

В архитектуре и source-документации хаба не должно быть hard-coded абсолютных путей к конкретной машине.

Используйте переносимые формы:

- `<AI_DOCS_HUB_ROOT>` для примеров команд;
- `<EXTERNAL_PROJECT_ROOT>` для внешних проектов;
- `${AI_DOCS_PROJECTS_ROOT}/project-name` в project configs;
- `__AI_DOCS_HUB_ROOT__` и `__PYTHON3_11__` в шаблонах, которые пользователь заполняет перед установкой.

Исключение: runtime-generated host files вне репозитория, например plist в `~/Library/LaunchAgents`, могут содержать реальные пути, потому что так требуют внешние launch/runtime-механизмы.

## Secrets

Никогда не документируйте secrets, credentials, tokens, cookies, private keys, sessions, dumps или secret-looking values.
