# 2026-05-20 - Documentation Coverage Checklist

## Что Изменилось

Documentation readiness расширен из минимального набора документов до coverage checklist проекта.

Теперь readiness считает:

- общий documentation coverage percent;
- coverage по категории `core`;
- coverage по категории `technical`.

## Новые Technical Разделы

В рекомендуемую структуру добавлены:

- `docs/operations/`;
- `docs/infrastructure/`;
- `docs/configuration.md`;
- `docs/security.md`;
- `docs/data.md`;
- `docs/integrations.md`;
- `docs/observability.md`;
- `docs/testing.md`;
- `docs/troubleshooting.md`;
- `docs/development.md`.

## Поведение

`lint_project`, `get_project_profile`, `healthcheck`, generated project overview и scaffold report теперь показывают или возвращают coverage metrics.

Scaffold может создать starter-файлы для всех новых разделов. Запись в подключенный проект по-прежнему требует явного `--write` или MCP `confirm=true`.

Documentation readiness gaps являются рекомендациями качества, а не operational health failure. Поэтому они остаются видимыми в healthcheck details, но не должны переводить status page в `degraded`.

## Проверка

Проверено на временном проекте: scaffold создает полный набор starter-файлов, после чего readiness возвращает `100.0%`.
