# Стандарт Документации

Документация является частью definition of done для изменений AI Docs Hub.

## Правило

Каждое значимое изменение хаба должно обновлять `/docs`.

Это строгое правило, которое нельзя игнорировать. Это не рекомендация на потом, а часть реализации.

Нельзя завершать изменение хаба, если из-за него появилась новая команда, зависимость, статусное поле, runtime workflow, MCP/RAG behavior, docs-site behavior, generated context behavior, project config behavior, agent workflow или architectural concept, но source-документация хаба и matching docs-site content остались старыми.

Если документацию нельзя обновить в том же change, реализация считается незавершенной и это нужно явно сообщить.

Это включает изменения в:

- RAG behavior;
- MCP tools или protocol behavior;
- docs-site behavior;
- правилах индексации;
- generated context files;
- runtime commands;
- commands;
- status fields;
- launch или supervision behavior;
- project config behavior;
- agent workflow;
- stack dependencies;
- operational workflows.

## Каталог Стандартов

В хабе сейчас используются такие группы стандартов:

- documentation standard: docs-as-code ownership, структура проектной документации, обязанность обновлять документацию хаба, change notes, generated files, path portability и secrets hygiene;
- [RAG policy](rag-policy.md): project namespaces, local indexing, secret-safe source filtering, search output metadata, watch mode и RAG freshness diagnostics;
- [MCP policy](mcp-policy.md): stdio JSON-RPC behavior, project scoping, stderr logging, подтверждение project-file writes и scoped Codex config edits;
- [llms.txt policy](llms-txt.md): generated LLM context files, input sources и запрет ручного редактирования;
- [runtime status standard](runtime-status.md): local Python 3.11, Node.js 22/npm 10, optional macOS `launchd`, foreground `hub-dev`, status endpoint и local storage;
- [project config standard](project-config.md): portable roots, isolated namespaces, `sources`, `include`, `exclude`, `agent_rules`, `docs_backend` и `mkdocs_config`;
- [source discovery standard](source-discovery.md): ручные include/exclude rules объединяются с безопасным MkDocs structural discovery, если он включен;
- [status diagnostics standard](status-diagnostics.md): `/status/` должен показывать global health и project-scoped diagnostics для projects, generated context, RAG, MkDocs и documentation readiness;
- [scaffold standard](scaffold.md): documentation scaffold по умолчанию dry-run, пишет только после явного подтверждения и не перезаписывает non-empty project files;
- [generated artifacts standard](generated-artifacts.md): derived files не редактируются вручную как source documentation;
- [security standard](security.md): secret-looking files и content должны исключаться из indexing и generated context.

Если новое поведение хаба не ложится в одну из этих групп, нужно добавить или расширить standard section до того, как считать поведение установленным.

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

## Project Config

Project configs хранятся в `configs/projects/*.yaml` и должны сохранять project context isolation:

- `project` и `namespace` задают project scope;
- `root` должен быть переносимым, например `${AI_DOCS_PROJECTS_ROOT}/project-name`;
- `sources`, `include` и `exclude` определяют readable surface;
- `agent_rules` передают project-specific instructions в profiles;
- `docs_backend` должен быть `auto`, `standard` или `mkdocs`;
- `mkdocs_config` должен быть относительным к project root.

Placeholder sample configs допустимы, но реальные project configs должны резолвиться в существующую директорию.

## MkDocs

MkDocs поддерживается как read-only adapter для source discovery:

- `docs_backend: auto` автоматически использует `mkdocs.yml`/`mkdocs.yaml`, если файл есть;
- `docs_backend: mkdocs` ожидает MkDocs-конфиг, но при его отсутствии показывает warning и продолжает по обычным `include`;
- `docs_backend: standard` игнорирует MkDocs.

Хаб может читать `site_name`, `docs_dir`, `site_dir`, `nav`, `exclude_docs`, `draft_docs`, `not_in_nav` и простое `INHERIT` для определения источников. Хаб не выполняет `plugins`, `hooks`, Python code или Markdown extensions из MkDocs-конфига.

## Runtime И Status

Runtime хаба local-first:

- Python 3.11 запускает scripts, Lite RAG, MCP, healthcheck, indexing, scaffold, watcher и generated context workflows;
- Node.js 22/npm 10 запускают Astro Starlight docs-site;
- `scripts/hub-dev` запускает docs-site и watcher в foreground;
- macOS `launchd` может запускать тот же supervisor persistently;
- `/status/` показывает global health и project-scoped diagnostics там, где это имеет смысл.

Status diagnostics должны отделять operational failures от recommendations. Documentation readiness gaps являются recommendations; stale или missing RAG indexes и missing generated artifacts являются operational warnings.

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
- `docs-site/src/content/docs/projects/*`;
- `docs-site/dist/`;
- runtime heartbeat и log files в `storage/runtime` и `storage/logs`.

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
