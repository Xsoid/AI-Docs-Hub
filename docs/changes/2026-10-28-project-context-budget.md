# Бюджет Размера `get_project_context`

## Что Изменилось

- Каталог skills в manifest содержит только `name` и `path`. Поля `status` (всегда `available`) и `description` удалены.
- Блок `decision_engine` содержит только `mode` и значения двух context-решений. Полный статус engine, fingerprint, versions, cache и latency в manifest больше не попадают.
- Decision Engine по-прежнему вычисляет оба решения при каждом вызове, поэтому shadow-метрики не меняются.
- `rag/project_context.py` задает `MANIFEST_BUDGET_BYTES = 4096`. Тест проверяет бюджет на synthetic-проекте с 6 instruction files и 15 skills.

## Почему

Baseline 2026-10-27 на шести подключенных проектах: 2,7–6,7 КБ, около 700–1700 токенов на вызов. Около 1,4 КБ в каждом проекте занимал shadow-блок `decision_engine`. Агенту он не нужен для ориентации. Описания skills агенты Claude Code и Codex и так загружают сами.

## Эксплуатация

- После изменения: 1,4–1,9 КБ на тех же проектах.
- Клиенту, который читал `skills[].description` или `decision_engine.status`, нужен `get_skill_inventory` или `get_decision_status`.
- Политика: `docs/standards/mcp-policy.md`.

## Проверка

```sh
make test
```

## Follow-Up

Optional `min_confidence` для `search_docs`, `search_decisions` и `search_modules` не реализован. Ишью требует не отсекать результаты без данных; набор оценки появится в задаче о качестве ранжирования.
