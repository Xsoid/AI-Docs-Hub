---
title: Status Diagnostics
description: hub-status components, required checks and JSON contract.
---

Status diagnostics должны показывать operational failures отдельно от documentation recommendations.

## Project Lifecycle

Optional component project-lifecycle показывает init status, quality profile availability, current fingerprint, verification, code review, security review, gate state, publishable flag и blocking reasons по каждому подключенному проекту. Status read-only и не запускает semantic review. Reports находятся в ignored storage/project-lifecycle/<project>/.

## Components

`scripts/hub-status` возвращает:

- `runtime` - foreground `hub-dev` или macOS `launchd`;
- `docs-site` - HTTP check docs-site URL;
- `repository` - `run_healthcheck`;
- `projects` - project configs and source discovery;
- `generated` - `llms*.txt`, report и generated project pages;
- `rag` - index state and freshness;
- `mkdocs` - adapter state;
- `docs-readiness` - coverage/recommendations;
- `skill-intelligence` - optional per-project skill audit freshness, counts and warnings;
- `mcp` - stdio MCP tool listing and healthcheck;
- `codebase-memory` - optional binary/version, local cache и indexed code graphs;
- `watcher` - heartbeat and child process state.

## Required Vs Optional

Required components define `DOWN`. Optional components can define `DEGRADED`.

`codebase-memory` является optional: отсутствующий binary, недоступный CLI или отсутствие графов дает warning/`DEGRADED`, но не `DOWN`.

`skill-intelligence` является optional: status читает сохраненные локальные audit reports из `storage/skill-intelligence/<project>/audit.json`, но сам audit не запускает. Запущенный watcher автоматически обновляет read-only audit после debounced изменения разрешенных project-docs; без watcher доступна явная dashboard action. Freshness audit определяется по SHA-256 содержимого разрешенных source-файлов; одно изменение `mtime` без изменения содержимого не считается stale. Старые reports без content hash временно используют legacy metadata до следующего audit. Отсутствующий или устаревший audit дает warning/`DEGRADED`; blocked или invalid report дает error внутри optional component.

Documentation readiness gaps are recommendations. Они должны оставаться видимыми, но не должны переводить repository/runtime status в degraded сами по себе.

## JSON Contract

```sh
python3.11 scripts/hub-status --json
```

Output содержит:

- `status`;
- `checked_at`;
- `exit_code`;
- `components`;
- per-component `status`, `message`, `required`, `details`.

RAG project details могут включать `secret_blocked_count`, `secret_blocked` и status `security_skipped`, если индекс свежий, но часть source files была пропущена secret scan.

Dashboard использует этот endpoint как source data.

Когда status JSON запрашивается из самого dashboard API, endpoint запускает `scripts/hub-status --json --docs-site-self-ok`. Это предотвращает рекурсивную HTTP-проверку docs-site из запроса, который уже доказывает, что dashboard/API обслуживаются.

## Fix Actions

Dashboard может показывать кнопки исправления только для allowlisted operational actions:

- `rag.reindex` - переиндексировать конкретный project namespace через `scripts/index-project --reindex` и затем регенерировать `llms*.txt`;
- `generated.refresh` - пересобрать generated project pages и `llms*.txt`;
- `codebase-memory.index` - после явного нажатия подготовить project-owned `.cbmignore` и построить scoped code graph;
- `skill-audit` - после явного нажатия выполнить read-only Skill Intelligence audit и сохранить локальный report;
- `docs-site.restart` - перезапустить persistent runtime через `scripts/hub-launchd restart`;
- `runtime.start` - запустить уже установленный LaunchAgent;
- `runtime.install-start` - установить и запустить LaunchAgent после явного нажатия пользователя.

Fix actions запускаются через локальный runtime endpoint:

```text
http://127.0.0.1:4322/apply-fix
http://127.0.0.1:4322/job
```

Runtime endpoint обслуживает:

```text
scripts/fix-server
scripts/apply-fix
```

Endpoint не принимает произвольные команды. Project-scoped actions должны валидировать project config, сохранять namespace isolation и проходить обычные exclude/secret-scan правила indexing.

Project details включают connection matrix для `docs-rag`, `generated-context` и `codebase-memory` со статусами `connected`, `attention` или `missing` и только allowlisted action для исправимого состояния. Codebase details дополнительно возвращают `mcp_configured`, `agent_rules_installed` и `fully_connected`; один graph index без agent onboarding не считается полным подключением.
