# 2026-10-03 - Project Control Center

## Что Изменилось

`/status/` переработан из плоской сетки компонентов в панель управления проектами. Самостоятельно показаны только global runtime-системы; project config, monitoring, Docs RAG, generated context, source discovery, documentation readiness, Skill Intelligence, Project Lifecycle и Codebase Memory теперь находятся внутри карточки соответствующего проекта.

Карточки получили рабочий редактор allowlisted полей project config. Внизу страницы добавлена форма подключения нового проекта. Обе формы используют localhost-only `POST /project-config` в `scripts/fix-server`; backend ограничивает browser-origin локальным dashboard, проверяет идентификаторы и путь `configs/projects/`, добавляет безопасные excludes при создании и пишет YAML атомарно. Успешное сохранение теперь также синхронно пересобирает generated project pages и `llms*.txt`, поэтому изменение названия сразу попадает в generated-документацию. Если пересборка не проходит, UI получает явное состояние: config сохранён, но derived-документация ещё не синхронизирована.

Stylesheet страницы объявлен global, потому что карточки строятся клиентским JavaScript. Это сохраняет оформление динамических system/project nodes и защищено отдельным regression-тестом.

## Проверка

- `python3.11 -m unittest tests.test_project_config_editor`;
- `python3.11 scripts/hub-status --json --docs-site-self-ok`;
- `./scripts/docs-npm run build`;
- visual smoke `/status/` на desktop и mobile widths.
