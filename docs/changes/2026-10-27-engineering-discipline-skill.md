# Engineering Discipline Skill

## Что Изменилось

Hub содержит собственный skill `.agents/skills/engineering-discipline/SKILL.md`. `AGENTS.md` требует применять его при написании и изменении кода вместо внешнего user-level skill `ub-mode`.

Skill — независимая формулировка идей https://github.com/unclebob/ub-mode. Текст оригинала не скопирован. Правило «Commit and Push» переписано: коммит и push выполняются только по запросу пользователя.

Заменяет routing из `2026-10-27-ub-mode-skill.md`.

## Почему

- У upstream `ub-mode` нет лицензии, а репозиторий Hub публичный. Копировать оригинал нельзя.
- Пользователь не хочет внешнюю зависимость. Собственный skill хранится в git Hub и не зависит от upstream.

## Эксплуатация

- Другие проекты получают skill через symlinks `~/.claude/skills/engineering-discipline` и `~/.codex/skills/engineering-discipline` на каталог skill в Hub. Изменение в Hub действует сразу, ручная синхронизация не нужна.
- Если checkout Hub перемещен или удален, symlinks не работают. Создайте их заново на новый путь.
- `crapper`, `dryer` и `mutator` не установлены. Агент сообщает такой gate как skipped.

## Проверка

```sh
make docs-check
python3.11 -m unittest discover -s tests
```

## Follow-Up

Установка `crapper`, `dryer` и `mutator` не выполнена.
