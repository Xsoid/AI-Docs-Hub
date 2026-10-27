# ub-mode Skill Routing

## Что Изменилось

`AGENTS.md` требует применять user-level skill `ub-mode` при написании и изменении кода Hub. Skill установлен вне репозитория: `~/.claude/skills/ub-mode/SKILL.md` и `~/.codex/skills/ub-mode/SKILL.md`. Upstream: https://github.com/unclebob/ub-mode.

Правила `AGENTS.md` и процедуры `.agents/skills/` имеют приоритет при конфликте. `docs/standards/documentation-hygiene.md` фиксирует, что внешний skill подключается ссылкой.

## Почему

Пользователь требует единые принципы разработки ub-mode для всех проектов, включая Hub.

## Эксплуатация

- Skill не копируется в репозиторий: у upstream нет лицензии.
- Без установленного skill правило не действует; установите его в каталоги выше.
- `crapper`, `dryer` и `mutator` не установлены. Агент сообщает такой gate как skipped.
- Требование ub-mode «Commit and Push» не отменяет правила коммитов Hub.

## Проверка

```sh
make docs-check
```

## Follow-Up

Установка `crapper`, `dryer` и `mutator` не выполнена.
