# Изоляция Storage В Тестах

## Что Изменилось

- `rag/config.py` владеет корнем storage (`STORAGE_DIR`). Переменная `HUB_STORAGE_DIR` переносит его. Пути Decision Engine, index, context snapshots, project lifecycle, Skill Intelligence, MCP audit и `scripts/generate-llms` выводятся из этого корня.
- `make test` запускает `unittest discover` с временным `HUB_STORAGE_DIR` и удаляет каталог после прогона.
- Guard Skill Intelligence принимает хранилище внутри репозитория Hub или внутри `STORAGE_DIR`.
- Пустой `MCP_AUDIT_DIR` считается незаданным.
- Регрессионный тест `tests/test_storage_isolation.py` проверяет, что каждый writer и `generate-llms` следуют `HUB_STORAGE_DIR`.

## Почему

Тесты писали кэш и метрики Decision Engine, `storage/generated/llms*`, записи MCP audit и данные Skill Intelligence в реальный `storage/`. В project-scoped storage появлялись namespace тестовых проектов, а `get_decision_status` смешивал реальные и тестовые данные.

## Эксплуатация

- Запускайте тесты через `make test`. Прямой `python3.11 -m unittest discover -s tests` по-прежнему пишет в реальный `storage/`.
- Тестовые namespace `context-project`, `synthetic-project` и `synthetic-lifecycle` удалены из локального `storage/decision-engine/`. Старые записи в `storage/mcp-audit/*.jsonl` удалит retention.

## Проверка

```sh
make test
```

Снимок `storage/` до и после `make test` совпадает, исключая логи и runtime живого сервиса.

## Follow-Up

Нет.
