# Project config schema v1

## Что изменилось

- Добавлен строгий versioned schema для `configs/projects/*.yaml`.
- `schema_version: 1` теперь используется во всех tracked-конфигах и в dashboard editor.
- Неизвестные поля, неверные типы, неверная версия и некорректные вложенные `sources` блокируются до построения `ProjectConfig`.
- Legacy-конфиги без версии продолжают работать, но `validate-configs` сообщает warning с migration hint.
- `validate_all_configs()` проверяет duplicate `project`/`namespace`, включая нормализацию имени.

## Проверка

- Добавлен `tests/test_project_config_schema.py` с проверками v1, legacy, schema errors, duplicate identities и semantic validation.
- Сохранены существующие path, docs backend и security checks.

## Follow-up

Пользовательские локальные bindings при необходимости переводятся на v1 явно; Hub не переписывает их автоматически.
