# GUI Dashboard

## Назначение

GUI dashboard - простая локальная страница состояния AI Docs Hub.

Адрес:

```text
http://localhost:4321/status/
```

Цель страницы - дать понятный ответ без чтения логов и JSON:

- хаб работает;
- хаб лежит;
- хаб работает не полностью;
- что именно проверено;
- какую команду выполнить дальше.

## Как Работает

Страница живет в `docs-site/src/pages/status.astro`.

Данные берутся из API endpoint:

```text
docs-site/src/pages/api/hub-status.json.ts
```

Endpoint запускает:

```sh
python3.11 scripts/hub-status --json
```

и возвращает JSON в браузер.

Страница обновляет состояние каждые 5 секунд и не выполняет опасных действий. Она не останавливает и не перезапускает runtime; для этого остаются явные команды в терминале.

## Что Видит Пользователь

Верхний блок показывает главный ответ:

- `Хаб работает`;
- `Хаб лежит`;
- `Хаб требует внимания`.

Ниже показаны понятные компоненты:

- `Пульт управления` - foreground или launchd runtime;
- `Веб-страница` - docs-site на `localhost:4321`;
- `Настройки` - repository healthcheck;
- `Поиск по документам` - Lite RAG;
- `Связь с Codex` - MCP bridge;
- `Автообновление` - watcher heartbeat.

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
```

Проверить страницу:

```sh
curl -I http://localhost:4321/status/
```

Проверить сборку:

```sh
./scripts/docs-npm run build
```
