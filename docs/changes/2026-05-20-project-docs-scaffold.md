# 2026-05-20 - Project Docs Scaffold

## Что Изменилось

Добавлен workflow для создания недостающих рекомендованных файлов документации подключенного проекта.

Новые команды:

```sh
make scaffold-docs PROJECT=project-name
make scaffold-docs-write PROJECT=project-name
```

`scaffold-docs` показывает план. `scaffold-docs-write` создает файлы в project root.

## Поведение

Scaffold использует documentation readiness diagnostics и создает starter-файлы для:

- `README.md`;
- `AGENTS.md`;
- `docs/index.md`;
- `docs/architecture/index.md`;
- `docs/modules/index.md`;
- `docs/decisions/index.md`;
- `docs/api/index.md`;
- `docs/deployment/index.md`;
- `docs/operations/index.md`;
- `docs/infrastructure/index.md`;
- `docs/configuration.md`;
- `docs/security.md`;
- `docs/data.md`;
- `docs/integrations.md`;
- `docs/observability.md`;
- `docs/testing.md`;
- `docs/troubleshooting.md`;
- `docs/development.md`;
- `docs/glossary.md`.

Если проект использует MkDocs, вместо `docs/` используется `docs_dir` из MkDocs-конфига.

Non-empty файлы не перезаписываются. Пустые recommended-файлы могут быть заполнены шаблоном, если пользователь не отключил это поведение.

Отчет scaffold показывает documentation coverage до и после выполнения.

## MCP

Добавлен MCP tool `scaffold_project_docs`. Он обязан требовать `confirm=true`, потому что пишет в подключенный проект. Без подтверждения возвращается safe dry-run response с командой для ручного запуска.

## Проверка

Выполнены:

- `python3.11 -m py_compile ...`;
- dry-run scaffold на временном проекте;
- write scaffold на временном проекте;
- `python3.11 scripts/mcp-test`;
- `./scripts/docs-npm run build`.

## Follow-Up

После scaffold в реальном проекте нужно запустить `make lint PROJECT=<name>` и при необходимости `make reindex PROJECT=<name>`.
