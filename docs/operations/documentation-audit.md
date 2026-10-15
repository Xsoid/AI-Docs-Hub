# Аудит Документации 2026-10-15

Этот отчёт фиксирует ревизию Issue #10. Он не задает новых нормативных правил. Текущие правила принадлежат указанным canonical documents.

| Проверенное утверждение | Canonical owner | Прежнее повторение или конфликт | Действие |
| --- | --- | --- | --- |
| Hub-документация обязательна для implementation change | `AGENTS.md`, Documentation Duty | `hub/agent-rules.md`, `hub/overview.md` повторяли прежнее требование о ручном docs-site mirror | Оставлен один routing rule; site pages стали navigation-only. |
| Hub source documentation находится в `docs/` | `docs/standards/documentation-hygiene.md` | README, docs landing и site pages повторяли ownership | Entry documents теперь ссылаются на стандарт. |
| Hub page generated from canonical Markdown нельзя редактировать | `docs/standards/generated-artifacts.md` | `AGENTS.md` требовал ручное matching-site update | Описан generator workflow и marker-safe cleanup. |
| Команды и runtime procedures | `docs/operations/command-reference.md`, `local-runtime.md` | README и `hub/usage.md` содержали самостоятельные runbooks | Entry pages ссылаются на canonical operations. |
| Style profile and STE limitation | `docs/standards/technical-writing.md` | Не было единого владельца | Добавлен один style guide и local audit limitation. |

Проверка кода подтвердила, что `scripts/generate-hub-pages` является фактическим источником рендеринга Hub pages. До исправления он не проверял output collision и не удалял stale marked output. Новые unit tests покрывают обе границы и `.gitignore` для нового generated Hub page.

Не устраненные semantic candidates не удаляются автоматикой. `scripts/audit-docs` сообщает advisory style candidates; владелец документа оценивает их без изменения исторических ADR и change notes.
