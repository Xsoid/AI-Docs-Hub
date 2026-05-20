# 2026-05-20 - Docs Site Coverage Restored

## Что Изменилось

Документация хаба приведена к фактической реализации:

- расширена навигация docs-site;
- добавлены site-страницы для local runtime, runtime observability, GUI dashboard, macOS menu bar и command reference;
- добавлены source-standards в `docs/standards/` для RAG, MCP, `llms.txt`, project config, source discovery, runtime/status, status diagnostics, scaffold, generated artifacts и security;
- matching standards pages добавлены в `docs-site/src/content/docs/standards/`;
- usage и overview страницы сайта теперь описывают generated context, scaffold, operation logs, lint, watcher, MCP tools и status diagnostics;
- явно зафиксировано, что default docs-site endpoint - `http://localhost:4321/`, не HTTPS.

## Поведение

Docs-site теперь показывает больше аспектов хаба, которые уже были в коде и частично в `/docs`, но были потеряны в опубликованной навигации.

Documentation readiness, generated artifacts, MkDocs source discovery, scaffold safety, MCP confirmation rules и runtime status теперь имеют отдельные страницы.

## Проверка

Проверить после изменения:

```sh
make docs-build
make healthcheck
git diff --check
```

## Follow-Up

Нет обязательного follow-up. Generated `llms*.txt` можно обновить через `make llms`, если нужен свежий derived context для локальных агентов.
