# Стандарт Документации

Документация является частью definition of done для изменений AI Docs Hub.

## Правило

Каждое значимое изменение хаба должно обновлять `/docs`.

Это не рекомендация на потом, а часть реализации. Нельзя завершать изменение хаба, если из-за него появилась новая команда, зависимость, статусное поле, runtime workflow, MCP/RAG behavior или architectural concept, но source-документация хаба осталась старой.

Это включает изменения в:

- RAG behavior;
- MCP tools или protocol behavior;
- docs-site behavior;
- правилах индексации;
- generated context files;
- runtime commands;
- launch или supervision behavior;
- project config behavior;
- agent workflow;
- stack dependencies;
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

## Подключенные Проекты

Хаб должен подталкивать проект к достаточной документационной структуре, но не должен ломать поиск только из-за неполной документации.

Для подключенного проекта рекомендуются:

- `README.md`;
- `AGENTS.md`;
- `docs/index.md`;
- `docs/architecture/`;
- `docs/modules/`;
- `docs/decisions/`;
- `docs/api/`;
- `docs/deployment/`;
- `docs/operations/`;
- `docs/infrastructure/`;
- `docs/configuration.md`;
- `docs/security.md`;
- `docs/data.md`;
- `docs/integrations.md`;
- `docs/observability.md`;
- `docs/testing.md`;
- `docs/troubleshooting.md`;
- `docs/development.md`;
- `docs/glossary.md`.

Если проект использует MkDocs, `docs_dir` из `mkdocs.yml` заменяет стандартный `docs/` как корень этих рекомендаций.

Отсутствующие или пустые разделы должны попадать в documentation readiness diagnostics как рекомендации. Это не config error и не причина смешивать контекст с другими проектами.

Documentation readiness recommendations не являются operational health failure. Они должны оставаться видимыми в `healthcheck` и project profile, но не должны переводить repository/runtime status в `degraded`, если нет реальных config warnings или errors.

Readiness должен считать общий documentation coverage percent и отдельное покрытие по категориям:

- `core` - обзор, правила агента, архитектура, модули, решения, API, деплой и glossary;
- `technical` - operations, infrastructure, configuration, security, data, integrations, observability, testing, troubleshooting и development.

## Scaffold Документации

Хаб может создать стартовые файлы для недостающих рекомендованных разделов:

```sh
make scaffold-docs PROJECT=project-name
make scaffold-docs-write PROJECT=project-name
```

Правила:

- `scaffold-docs` только показывает план и не меняет подключенный проект;
- `scaffold-docs-write` является явным разрешением на запись в project root;
- MCP-инструмент для scaffold обязан требовать `confirm=true`;
- non-empty файлы нельзя перезаписывать;
- пустые recommended-файлы можно заполнить шаблоном, если пользователь не отключил это поведение;
- шаблоны не должны содержать секреты или host-specific значения.

## MkDocs

MkDocs поддерживается как read-only adapter для source discovery:

- `docs_backend: auto` автоматически использует `mkdocs.yml`/`mkdocs.yaml`, если файл есть;
- `docs_backend: mkdocs` ожидает MkDocs-конфиг, но при его отсутствии показывает warning и продолжает по обычным `include`;
- `docs_backend: standard` игнорирует MkDocs.

Хаб может читать `site_name`, `docs_dir`, `site_dir`, `nav`, `exclude_docs`, `draft_docs`, `not_in_nav` и простое `INHERIT` для определения источников. Хаб не выполняет `plugins`, `hooks`, Python code или Markdown extensions из MkDocs-конфига.

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
