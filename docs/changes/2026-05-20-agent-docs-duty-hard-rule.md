# 2026-05-20 - Agent Docs Duty Hard Rule

## Что Изменилось

`AGENTS.md` получил отдельный non-negotiable documentation rule.

Теперь правило явно говорит, что любое изменение AI Docs Hub, затрагивающее architecture, RAG, MCP, docs-site, indexing, generated context, project config behavior, runtime, operations, stack dependencies, commands, status fields или agent workflow, должно в том же change обновлять:

- source documentation в `docs/`;
- matching docs-site content в `docs-site/src/content/docs/`;
- `docs/changes/` note, если поведение влияет на usage, operations, debugging или extension.

## Поведение

Агент не должен завершать изменение хаба, оставляя документацию follow-up. Если документацию нельзя обновить в том же change, реализация считается незавершенной.

## Проверка

Проверить после изменения:

```sh
make docs-build
git diff --check
```

## Follow-Up

Нет.
