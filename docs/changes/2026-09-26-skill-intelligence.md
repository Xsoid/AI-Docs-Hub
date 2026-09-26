# 2026-09-26 - Skill Intelligence

## Что изменилось

В Hub добавлен deterministic Skill Architecture audit для разрешенной документации, root `AGENTS.md` и `.agents/skills/*/SKILL.md`. Audit инвентаризирует skills, классифицирует материалы и выдает объяснимые workflow candidates и quality diagnostics без LLM/API. Междокументные workflow-дубликаты теперь сравниваются по содержимому, а ownership-проверка сопоставляет skills с canonical `docs/` и `AGENTS.md`.

Добавлены `make skill-audit PROJECT=name` и `scripts/skill-audit --project name --json`, project-scoped MCP tools для inventory/analyze/validate/proposals и proposal apply. `get_project_profile` теперь содержит компактный `skill_intelligence` summary, не раскрывающий project-derived текст. Audit/proposal JSON сохраняется в ignored `storage/skill-intelligence/<project>/`. Запись во внешний проект требует reviewed replacement content, exact proposal targets и `confirm=true`; apply повторно проверяет containment, excludes, secret scan и hash существующего target, а запись в checkout Hub запрещена.

Skill evolution представлен только proposal API и требует подтвержденного evidence. Ни audit, ни proposal не изменяют проект автоматически. Project-derived данные внешних проектов не записываются в tracked source/docs Hub.

## Проверка

- Synthetic external-project regression tests проверяют отсутствие tracked Hub изменений, ignored local storage, explicit apply и project-root boundary.
- Unit tests проверяют inventory, candidate classifications, междокументные дубликаты с разными заголовками, skill/docs ownership, profile summary, MCP scoping, proposal confirmation и evolution evidence.
- Python compilation, CLI wiring, MCP tests, healthcheck и docs-site build проверены перед завершением implementation.

## Follow-up

Нет: ранее выявленные gaps по междокументным дубликатам, skill/docs ownership и profile summary закрыты в текущем change set.
