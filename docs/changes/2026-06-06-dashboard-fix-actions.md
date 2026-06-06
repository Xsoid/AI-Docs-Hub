# 2026-06-06 - Dashboard Fix Actions

## Что Изменилось

- Status dashboard получил allowlisted fix actions через local fix server `http://127.0.0.1:4322`.
- Добавлены `scripts/fix-server` и `scripts/apply-fix` для фоновых repair jobs с состоянием в `storage/runtime/fixes/` и логами `storage/logs/apply-fix-*.log`.
- `rag.reindex` исправляет stale/missing/error RAG index для одного project namespace, затем регенерирует `llms*.txt`.
- Lite RAG reindex теперь пропускает suspicious source files вместо индексации их содержимого; пропуски сохраняются в index security metadata и отображаются как `security_skipped`.
- Dashboard status API запускает `hub-status` с `--docs-site-self-ok`, чтобы не делать рекурсивный HTTP healthcheck в тот же Astro process.
- `hub-dev` запускает fix server как child process, хранит `health_url` в runtime heartbeat, но supervisor readiness/monitoring использует TCP-listen; HTTP-проверка остается в `hub-status`/dashboard.

## Причина

Dashboard показывал проблемы в `Веб-страница` и `Поиск по документам`: web check мог уходить в timeout из-за рекурсивной проверки во время status API запроса, а RAG показывал stale index без кнопки исправления.

## Проверка

```sh
python3.11 scripts/hub-status --json --docs-site-self-ok
python3.11 scripts/apply-fix --json --action rag.reindex --project <project>
./scripts/docs-npm run build
```
