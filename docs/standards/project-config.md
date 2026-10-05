# Project Config Standard

Project configs живут в:

```text
configs/projects/*.yaml
```

Они описывают, какие project files хаб может читать, как изолировать namespace и какие правила передавать агентам.

## Schema v1

Tracked-конфиги используют `schema_version: 1`. Loader сначала проверяет raw YAML, затем применяет defaults и только после этого строит `ProjectConfig`. Разрешены только поля `schema_version`, `project`, `namespace`, `title`, `root`, `docs_backend`, `mkdocs_config`, `sources`, `include`, `exclude` и `agent_rules`; неизвестное поле, неверный scalar/list/object или неверный `schema_version` блокирует конфиг с машинно-читаемыми `level`, `code`, `field` и совместимым `message`.

`project` и `root` обязательны. `namespace` по умолчанию равен `project`, `title` по умолчанию равен `project`, `docs_backend` по умолчанию равен `auto`, `mkdocs_config` - `mkdocs.yml`, остальные списки по умолчанию пусты. `sources` содержит объекты только с непустыми строковыми `path` и `type`; `include` должен содержать хотя бы один pattern после semantic validation.

Конфиг без `schema_version` считается legacy текущего формата: он продолжает загружаться и проходит прежние path/security checks, но `make validate-configs` выводит warning `legacy_config` с рекомендацией добавить `schema_version: 1`. Пользовательские локальные configs автоматически не переписываются. Конфликты `project` и `namespace`, включая коллизии после нормализации, блокируются централизованно в `validate_all_configs()`.

## Обязательные Поля

- `project` - стабильный project id.
- `namespace` - RAG/MCP namespace.
- `root` - project root, желательно переносимый.
- `include` - allowed read surface.

## Рекомендуемые Поля

- `title` - human readable название.
- `docs_backend` - `auto`, `standard` или `mkdocs`.
- `mkdocs_config` - relative path к MkDocs config.
- `sources` - структурное описание источников.
- `exclude` - запретные paths.
- `agent_rules` - project-specific rules для agents.

## Path Portability

В committed configs нельзя hard-code absolute paths конкретной машины.

Используйте:

- `${AI_DOCS_PROJECTS_ROOT}/project-name`;
- relative path от root хаба;
- placeholder `<EXTERNAL_PROJECT_ROOT>` только для sample configs.

Host-specific absolute path допустим только во внешнем локальном config, который не коммитится.

## docs_backend

- `auto` - default; использует MkDocs structural discovery, если найден `mkdocs.yml` или `mkdocs.yaml`.
- `mkdocs` - ожидает MkDocs config; если config отсутствует, пишет warning и продолжает по include rules.
- `standard` - игнорирует MkDocs и использует только configured `sources`/`include`/`exclude`.

## Validation

```sh
make validate-configs
```

Validation отличает:

- errors: config не пригоден для indexing;
- warnings: config работает, но требует внимания;
- recommendations: documentation readiness gaps, не operational failure.

## Dashboard Editor

`/status/` может явно создать или обновить project config через localhost-only `POST http://127.0.0.1:4322/project-config`. Редактор принимает только allowlisted поля, не меняет project id существующего config, проверяет slug/namespace, добавляет базовые secret-exclude patterns при создании и атомарно публикует YAML только внутри `configs/projects/`. В этом dashboard-потоке YAML — source of truth: сразу после записи endpoint пересобирает generated project pages и `llms*.txt`; только после этого форма сообщает об успехе. При сбое генерации API сообщает о сохранённой конфигурации и не выдаёт её за синхронизированную документацию.

## Local-Only Project Bindings

Подключение конкретного проекта к локальному Hub является local-only операцией. Создание или обновление `configs/projects/*.yaml`, индекса проекта, generated project page, `llms*.txt`, Codebase Memory cache, project-scoped MCP entry или managed routing rules не должно создавать или изменять tracked-файлы в `docs/`, `docs-site/` или `docs/changes/`.

Change note создается только при изменении самой политики или реализации подключения в AI Docs Hub. Для обычного onboarding отдельного проекта достаточно локального binding, generated artifacts и runtime status.

Skill Intelligence работает в scope выбранного project config и namespace. Он читает effective documentation sources, а также только root `AGENTS.md` и `.agents/skills/*/SKILL.md`; эти agent paths не требуют добавления в docs include list, но проходят общие exclude/path/secret checks. Audit и proposal artifacts остаются в ignored `storage/skill-intelligence/<project>/`, а apply может менять только явно заявленные разрешенные пути внешнего project root.
