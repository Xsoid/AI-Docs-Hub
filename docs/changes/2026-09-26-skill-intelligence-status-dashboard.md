# 2026-09-26 - Skill Intelligence в status dashboard

## Что изменилось

`/status/` и `scripts/hub-status --json` теперь показывают optional component `skill-intelligence` по каждому подключенному проекту. В карточке видны наличие и свежесть audit, количество skills и workflow candidates, high-confidence candidates, warnings/errors и изменившиеся source-файлы.

Dashboard не запускает audit автоматически. Кнопка `Запустить audit` или `Обновить audit` вызывает только allowlisted `skill-audit`: анализ read-only, результат сохраняется в ignored `storage/skill-intelligence/<project>/audit.json`, файлы подключенного проекта не изменяются.

## Проверка

- `./.venv/bin/python -m unittest -v tests.test_skill_intelligence` — 17/17 passed;
- `npm run build` в `docs-site/` — 39 страниц собраны;
- `make healthcheck` и `make mcp-test` — passed;
- пять реальных project configs прошли `scripts/lint-project` с exit code 0; найденные issues отображаются как audit diagnostics, а placeholder `example-project` исключен из этого прогона из-за `<EXTERNAL_PROJECT_ROOT>`;
- `/api/hub-status.json` после аудита показывает `5/5 project audits available`, все audit fresh.
