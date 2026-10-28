# Retention Для Reviews, Fix Jobs И Operation Log

## Что Изменилось

- `project-lifecycle/{project}/reviews/` хранит последние 50 fingerprint (`MAX_REVIEW_FINGERPRINTS`). Лишние каталоги удаляются после каждой записи `verification.json` или `*-review.json`.
- `runtime/fixes/` хранит последние 50 job JSON (`MAX_FIX_JOBS`). Лишние файлы удаляются, когда `scripts/apply-fix` создает новый job.
- `index/{project}_log.jsonl` хранит последние 1000 записей (`MAX_OPERATION_LOG_ENTRIES`). После каждой записи `log_operation` атомарно переписывает файл, если записей больше.
- `keep_newest()` из `rag/storage_retention.py` удаляет и каталоги, не только файлы.
- `docs/standards/generated-artifacts.md` описывает новые лимиты.

## Почему

Каталог `reviews/` получал новый каталог на каждый patch fingerprint: в одном проекте 268 каталогов, 3 МБ. Job JSON и operation log тоже росли без ограничения.

## Эксплуатация

- Gate не ломается: запись делает свой fingerprint самым новым по времени изменения, поэтому `get_pre_publish_status` и `review_status` всегда находят review текущего patch.
- Review старого fingerprint, вышедшего за лимит, удаляется. Если вернуть patch к такому состоянию, verification и reviews нужно выполнить заново.
- Накопленные данные сокращаются при первой новой записи в соответствующее место. Отдельная команда не нужна.
- Job, который удален retention во время выполнения, создается заново при завершении, но без начальных полей.

## Проверка

```sh
make test
```
