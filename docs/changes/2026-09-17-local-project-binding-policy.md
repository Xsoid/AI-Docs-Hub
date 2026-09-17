# 2026-09-17 - Политика локальных project bindings

## Что изменилось

Зафиксировано, что onboarding отдельного проекта в локальный AI Docs Hub не создает tracked-документацию. Локальными считаются project config, индексы, generated artifacts, Codebase Memory cache, project-scoped MCP entry и managed routing rules.

Такие операции не должны изменять `docs/`, `docs-site/` или `docs/changes/`. Change note создается только при изменении самой политики или реализации onboarding.
