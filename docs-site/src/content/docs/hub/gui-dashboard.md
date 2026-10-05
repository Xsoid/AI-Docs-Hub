---
title: GUI Dashboard
description: Локальная страница состояния AI Docs Hub.
---

GUI dashboard - локальная панель управления хабом и подключенными проектами с ограниченными fix-действиями.

Адрес:

```text
http://localhost:4321/status/
```

## Как Работает

Страница живет в:

```text
docs-site/src/pages/status.astro
```

Карточки систем и проектов создаются клиентским JavaScript после получения status JSON. Поэтому stylesheet standalone-страницы объявлен global: Astro-scoped selectors не применяются к динамически созданным DOM nodes.

Данные берутся из:

```text
docs-site/src/pages/api/hub-status.json.ts
```

Endpoint запускает:

```sh
python3.11 scripts/hub-status --json --docs-site-self-ok
```

Страница обновляет состояние каждые 10 секунд. Кнопка `Обновить` делает тот же запрос без cache и не запускает параллельную проверку, если предыдущий запрос еще идет. При открытом редакторе проекта автоматическая перерисовка приостанавливается.

Dashboard может запускать только заранее разрешенные fix-действия через кнопку пользователя. Endpoint не принимает произвольные shell-команды и не редактирует source-документацию подключенных проектов.

После нажатия fix-кнопки панель `Операции` остается видимой до следующего запуска и показывает action/project, этап `Запуск` → `В очереди` → `Выполняется` → `Готово` или `Ошибка`, progress indicator, job id, elapsed time и итоговое сообщение. Активная кнопка получает spinner, а остальные fix-кнопки временно блокируются. После успеха dashboard автоматически обновляет component status, не скрывая итог операции.

Fix API:

```text
http://127.0.0.1:4322/apply-fix
http://127.0.0.1:4322/job
http://127.0.0.1:4322/project-config
```

Исполнители:

```text
scripts/fix-server
scripts/apply-fix
```

Фоновые jobs и логи пишутся в:

```text
storage/runtime/fixes/
storage/logs/apply-fix-*.log
```

## Информационная Архитектура

Runtime, docs-site, repository health, MCP bridge и watcher являются самостоятельными global-блоками. Все project-scoped данные собраны в карточке соответствующего проекта: config/root/namespace, Docs RAG, Generated context, source discovery, documentation readiness, Skill Intelligence, Project Lifecycle и Code graph.

В каждой карточке доступны monitoring и allowlisted действия подключения. Раскрываемая форма редактирует `title`, `root`, `namespace`, `docs_backend`, `mkdocs_config`, `include` и `exclude`; project id остаётся неизменяемым. Нижняя форма создаёт новый config с обязательными secret-exclude patterns через localhost-only `POST /project-config`. Запись атомарна и ограничена `configs/projects/`; после неё endpoint синхронно пересобирает project pages и `llms*.txt`. Поэтому успешный ответ формы означает, что новое имя и другие config-поля уже отражены в generated-документации; при ошибке ответ отдельно сообщает, если YAML был сохранён, а derived-артефакты ещё нет.

Для `Поиск по документам` dashboard всегда показывает `Актуализировать` у существующего project index, а для `missing` или `error` — `Собрать индекс`. Кнопка запускает `rag.reindex` для одного project namespace через локальный fix server и не обходит secret scan.

Карточка `Проекты` показывает для каждого проекта подключения к Docs RAG, Generated context и Code graph. Для отсутствующих подключений доступны allowlisted кнопки:

- `rag.reindex` - собрать или актуализировать docs index;
- `generated.refresh` - пересобрать project pages и `llms*.txt`;
- `skill-audit` - выполнить read-only Skill Intelligence audit и обновить локальный report;
- `codebase-memory.index` - создать project-owned `.cbmignore`, если его нет, и построить moderate code graph с `persistence=false`.
- `project.repair` - кнопка `Привести в порядок` в header неполной matrix: безопасно quarantine-ит exact blocked source paths только в Hub binding и затем пересобирает все derived artifacts проекта.

Если Generated context остановлен secret scan, карточка показывает число blocked sources и не предлагает бесполезно повторять `Собрать context`. `project.repair` не раскрывает содержимое файла и не меняет подключенный project: он добавляет уже заблокированные project-relative paths в `exclude` локального Hub config, после чего rebuild-ит project page, RAG и context.

Code graph считается подключенным только при `graph indexed + project-scoped MCP configured + managed AGENTS rules installed`. Если существует только graph index, dashboard показывает `требует внимания` и кнопку `Завершить подключение`. После успешного onboarding панель операции напоминает перезапустить Codex.

Для `Веб-страница` и runtime dashboard может показать кнопку restart/start persistent runtime через `launchd`, когда проблема видна из status JSON и dashboard сам остается доступен.

## Ограничение Static Build

При `astro build` endpoint `/api/hub-status.json` генерируется как static artifact на момент сборки. Для живого статуса нужен локальный runtime:

```sh
make hub-dev
```

или:

```sh
make hub-start
```

## Проверка

```sh
curl -sS http://localhost:4321/api/hub-status.json | python3.11 -m json.tool
curl -sS 'http://127.0.0.1:4322/apply-fix?action=rag.reindex&project=project-name' | python3.11 -m json.tool
curl -sS -X POST http://127.0.0.1:4322/project-config -H 'content-type: application/json' --data @project-config.json | python3.11 -m json.tool
curl -I http://localhost:4321/status/
```
