# Retention И Orphan Storage

## Что Изменилось

- `capture_project_context` хранит последние 50 snapshots на проект (`MAX_CONTEXT_SNAPSHOTS`). Порядок определяет время изменения файла, затем имя, поэтому несколько snapshots в одну секунду удаляются в правильном порядке.
- Новый модуль `rag/storage_retention.py`:
  - `project_locations()` перечисляет project-scoped места в `storage/`;
  - `find_orphans()` и `remove_orphans()` находят и удаляют записи проектов без config;
  - `keep_newest()` - общая retention по количеству. Она заменила `prune_logs` из `rag/runtime_logs.py`, `scripts/apply-fix` использует ее.
- `scripts/storage-prune` и `make storage-prune`: по умолчанию dry-run, удаление только с `--apply`.
- `make hub-status` и `/status/` показывают компонент `storage` с warning об orphan storage.
- `docs/standards/generated-artifacts.md` описывает политику хранения каждого каталога `storage/`.

## Почему

Context snapshots копились без удаления. После удаления project config его index, reports, cache и graph оставались в `storage/` и путали диагностику.

## Эксплуатация

- В локальном checkout `make storage-prune` находит `ai-docs-hub`: index и Skill Intelligence report без config, 20,7 МБ. Удаление выполняется только явным `--apply`.
- `remove_orphans()` удаляет только прямых потомков project-scoped мест и отказывается от других путей.
- Невалидный project config останавливает команду до удаления.

## Проверка

```sh
make test
make storage-prune
make hub-status
```

## Follow-Up

- Retention для `project-lifecycle/{project}/reviews/`, `runtime/fixes/` и operation log описывает `docs/changes/2026-10-28-review-and-log-retention.md`.
