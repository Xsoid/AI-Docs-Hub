---
title: GUI Dashboard
description: Локальная страница состояния AI Docs Hub.
---

GUI dashboard - локальная страница состояния с ограниченными fix-действиями.

Адрес:

```text
http://localhost:4321/status/
```

## Как Работает

Страница живет в:

```text
docs-site/src/pages/status.astro
```

Данные берутся из:

```text
docs-site/src/pages/api/hub-status.json.ts
```

Endpoint запускает:

```sh
python3.11 scripts/hub-status --json --docs-site-self-ok
```

Страница обновляет состояние каждые 5 секунд. Кнопка `Обновить` делает тот же запрос без cache и не запускает параллельную проверку, если предыдущий запрос еще идет.

Dashboard может запускать только заранее разрешенные fix-действия через кнопку пользователя. Endpoint не принимает произвольные shell-команды и не редактирует source-документацию подключенных проектов.

После нажатия fix-кнопки панель `Операции` остается видимой до следующего запуска и показывает action/project, этап `Запуск` → `В очереди` → `Выполняется` → `Готово` или `Ошибка`, progress indicator, job id, elapsed time и итоговое сообщение. Активная кнопка получает spinner, а остальные fix-кнопки временно блокируются. После успеха dashboard автоматически обновляет component status, не скрывая итог операции.

Fix API:

```text
http://127.0.0.1:4322/apply-fix
http://127.0.0.1:4322/job
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

## Компоненты На Странице

- `Пульт управления` - foreground или `launchd` runtime.
- `Веб-страница` - docs-site на `localhost:4321`.
- `Настройки` - repository healthcheck.
- `Проекты` - project configs и source discovery.
- `Generated context` - `llms*.txt`, report и generated project pages.
- `Поиск по документам` - Lite RAG.
- `MkDocs` - adapter diagnostics.
- `Documentation readiness` - coverage и recommendations.
- `Связь с Codex` - MCP bridge.
- `Граф исходного кода` - Codebase Memory.
- `Автообновление` - watcher heartbeat.

Для `Поиск по документам` dashboard всегда показывает `Актуализировать` у существующего project index, а для `missing` или `error` — `Собрать индекс`. Кнопка запускает `rag.reindex` для одного project namespace через локальный fix server и не обходит secret scan.

Карточка `Проекты` показывает для каждого проекта подключения к Docs RAG, Generated context и Code graph. Для отсутствующих подключений доступны allowlisted кнопки:

- `rag.reindex` - собрать или актуализировать docs index;
- `generated.refresh` - пересобрать project pages и `llms*.txt`;
- `codebase-memory.index` - создать project-owned `.cbmignore`, если его нет, и построить moderate code graph с `persistence=false`.

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
curl -I http://localhost:4321/status/
```
