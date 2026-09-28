# 2026-09-28 - Автообновление Skill Intelligence после изменений проекта

## Что изменилось

Watcher AI Docs Hub после debounced изменения разрешенных project-docs теперь не только переиндексирует RAG и generated context, но и запускает read-only Skill Intelligence audit. Это убирает ручное окно, в котором status показывает `STALE` после обычной доработки подключенного проекта.

Audit не меняет файлы подключенного проекта и сохраняет только derived report в ignored `storage/skill-intelligence/<project>/`. При необходимости поведение можно отключить флагом `scripts/watch-project --all --no-skill-audit` (или указать `--project name`); в этом режиме `STALE` остается честным сигналом необновленного audit.

Если indexing или audit временно завершается ошибкой, watcher повторяет тот же snapshot после короткой задержки; до успешного обновления статус не маскируется под fresh.

## Проверка

- `make skill-audit PROJECT=mammonite` обновил текущий report;
- `python3 scripts/hub-status --json` показывает для `mammonite` `audited/fresh`, `changed_paths: []`, `0` warnings и `0` errors;
- unit tests и docs build выполняются после изменения watcher.
