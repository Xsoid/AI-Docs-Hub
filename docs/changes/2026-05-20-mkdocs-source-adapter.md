# 2026-05-20 - MkDocs Source Adapter

## Что Изменилось

Хаб получил read-only adapter для проектов, которые уже ведут документацию через MkDocs.

Project config теперь поддерживает:

- `docs_backend: auto`;
- `docs_backend: mkdocs`;
- `docs_backend: standard`;
- `mkdocs_config: "mkdocs.yml"`.

В режиме `auto` хаб использует `mkdocs.yml` или `mkdocs.yaml`, если файл есть, но не требует его наличия. В режиме `mkdocs` отсутствие конфига становится warning, а не hard error.

## Поведение

Adapter безопасно читает только структурные поля MkDocs:

- `site_name`;
- `docs_dir`;
- `site_dir`;
- `nav`;
- `exclude_docs`;
- `draft_docs`;
- `not_in_nav`;
- простое `INHERIT` внутри project root.

Хаб не выполняет MkDocs `plugins`, `hooks`, Python code или Markdown extensions. Все источники все равно проходят обычные include/exclude правила, secret scan и project namespace isolation.

## Documentation Readiness

Добавлена диагностика полноты документации проекта. Она проверяет наличие `README.md`, `AGENTS.md`, архитектуры, модулей, decisions, API, deployment и glossary.

Недостающие разделы отображаются как рекомендации в config validation, healthcheck, project profile, lint report и generated project overview. Это не блокирует поиск и индексацию.

## Status Page

`/status/` показывает отдельный компонент `MkDocs`. Он выводит по проектам выбранный `docs_backend`, найден ли MkDocs config, активен ли adapter, какой `docs_dir` используется, и warnings для принудительного `docs_backend: mkdocs`.

Если проект работает в `docs_backend: auto` и не содержит `mkdocs.yml`, это отображается как обычное состояние, а не как degraded status.

## Проверка

Выполнены:

- `python3.11 -m py_compile rag/*.py mcp/server.py scripts/index-project scripts/generate-llms scripts/generate-project-pages scripts/watch-project scripts/healthcheck scripts/validate-configs scripts/lint-project`;
- `python3.11 scripts/validate-configs`;
- `python3.11 scripts/healthcheck`;
- ad-hoc проверка MkDocs `docs_dir` и `exclude_docs` на временном проекте.

## Follow-Up

Если появятся проекты со сложными MkDocs plugins, adapter должен оставаться read-only: лучше расширять безопасный парсер структурных полей, чем выполнять проектный Python-код.
