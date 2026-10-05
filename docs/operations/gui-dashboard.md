# GUI Dashboard

## Назначение

GUI dashboard - локальная панель управления AI Docs Hub и подключенными проектами.

Адрес:

```text
http://localhost:4321/status/
```

В footer status dashboard и обычного docs-site выводится кликабельный `© Xsoid.Net`, ведущий на `https://xsoid.net/`.

Цель страницы - дать понятный ответ без чтения логов и JSON:

- хаб работает;
- хаб лежит;
- хаб работает не полностью;
- что именно проверено;
- какую команду выполнить дальше.

## Как Работает

Страница живет в `docs-site/src/pages/status.astro`.

Карточки систем и проектов создаются клиентским JavaScript после получения status JSON. Поэтому stylesheet standalone-страницы объявлен global: Astro-scoped selectors не применяются к динамически созданным DOM nodes.

Данные берутся из API endpoint:

```text
docs-site/src/pages/api/hub-status.json.ts
```

Endpoint запускает:

```sh
python3.11 scripts/hub-status --json --docs-site-self-ok
```

и возвращает JSON в браузер.

Страница обновляет состояние каждые 10 секунд и не запускает параллельную проверку, если предыдущий запрос еще идет. Пока открыта форма редактирования проекта, автоматическая перерисовка приостанавливается, чтобы не потерять введённые данные.

Dashboard может запускать только заранее разрешенные fix-действия через кнопку пользователя. Endpoint не принимает произвольные shell-команды и не редактирует source-документацию подключенных проектов.

После нажатия fix-кнопки панель `Операции` остается видимой до следующего запуска и показывает action/project, этап `Запуск` → `В очереди` → `Выполняется` → `Готово` или `Ошибка`, progress indicator, job id, elapsed time и итоговое сообщение. Активная кнопка получает spinner, а остальные fix-кнопки временно блокируются. После успеха dashboard автоматически обновляет component status, не скрывая итог операции.

Fix API:

```text
http://127.0.0.1:4322/apply-fix
http://127.0.0.1:4322/job
http://127.0.0.1:4322/project-config
```

`POST /project-config` не ограничивается записью YAML: после успешного create/update он синхронно запускает генерацию project pages и `llms*.txt`. Поэтому изменение названия проекта в карточке отражается в generated-документации до успешного ответа UI. Если генерация не проходит, ответ `500` содержит `config_saved: true`: конфигурация сохранена, но документация ещё требует повторной синхронизации.

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

Кнопка `Обновить` вручную запрашивает этот же endpoint без кеша, временно показывает состояние обновления и не запускает параллельную проверку, если предыдущий запрос еще идет.

## Что Видит Пользователь

Верхний блок показывает главный ответ:

- `Хаб работает`;
- `Хаб лежит`;
- `Хаб требует внимания`.

Самостоятельными блоками показаны только системы хаба, не принадлежащие отдельному проекту:

- `Пульт управления` - foreground или launchd runtime;
- `Веб-страница` - docs-site на `localhost:4321`;
- `Настройки` - repository healthcheck;
- `Связь с Codex` - MCP bridge;
- `Автообновление` - watcher heartbeat.

Ниже создаётся один полноценный блок на проект. Внутри него находятся config/root/namespace, monitoring и project-scoped подсистемы: Docs RAG, Generated context, source discovery, documentation readiness, Skill Intelligence, Project Lifecycle и Code graph.

Для `Поиск по документам` dashboard всегда показывает `Актуализировать` у существующего project index, а для `missing` или `error` — `Собрать индекс`. Кнопка запускает `rag.reindex` для одного project namespace через локальный fix server и не обходит secret scan.

Карточка `Проекты` показывает для каждого проекта подключения к Docs RAG, Generated context и Code graph. Для отсутствующих подключений доступны allowlisted кнопки:

- `rag.reindex` - собрать или актуализировать docs index;
- `generated.refresh` - пересобрать project pages и `llms*.txt`;
- `codebase-memory.index` - создать project-owned `.cbmignore`, если его нет, и построить moderate code graph с `persistence=false`.
- `project.repair` - кнопка `Привести в порядок` в header неполной matrix: безопасно quarantine-ит exact blocked source paths только в Hub binding и затем пересобирает все derived artifacts проекта.

Если Generated context остановлен secret scan, карточка показывает число blocked sources и не предлагает бесполезно повторять `Собрать context`. `project.repair` не раскрывает содержимое файла и не меняет подключенный project: он добавляет уже заблокированные project-relative paths в `exclude` локального Hub config, после чего rebuild-ит project page, RAG и context.

Code graph считается подключенным только при `graph indexed + project-scoped MCP configured + managed AGENTS rules installed`. Если существует только graph index, dashboard показывает `требует внимания` и кнопку `Завершить подключение`. После успешного onboarding панель операции напоминает перезапустить Codex.

Для `Веб-страница` и runtime dashboard может показать кнопку restart/start persistent runtime через `launchd`, когда проблема видна из status JSON и dashboard сам остается доступен.

Раскрываемая форма проекта редактирует `title`, `root`, `namespace`, `docs_backend`, `mkdocs_config`, `include` и `exclude`. Project id после создания неизменяем. Форма внизу создаёт новый project config; базовые secret-exclude patterns добавляются автоматически. `scripts/fix-server` проверяет payload и атомарно публикует YAML только внутри `configs/projects/`.

## Ограничения

Dashboard является live-интерфейсом для dev/runtime-режима `hub-dev`.

При `astro build` endpoint `/api/hub-status.json` генерируется как static artifact на момент сборки. Для живого статуса нужно использовать запущенный локальный runtime:

```sh
make hub-dev
```

или persistent-режим:

```sh
make hub-start
```

Для быстрого доступа из верхнего бара macOS можно запустить menu bar helper:

```sh
make hub-menu-start
```

Он открывает dashboard и документацию через системное меню.

## Проверка

Проверить API:

```sh
curl -sS http://localhost:4321/api/hub-status.json | python3.11 -m json.tool
curl -sS 'http://127.0.0.1:4322/apply-fix?action=rag.reindex&project=project-name' | python3.11 -m json.tool
curl -sS -X POST http://127.0.0.1:4322/project-config -H 'content-type: application/json' --data @project-config.json | python3.11 -m json.tool
```

Проверить страницу:

```sh
curl -I http://localhost:4321/status/
```

Проверить сборку:

```sh
./scripts/docs-npm run build
```
