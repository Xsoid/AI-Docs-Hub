# Status Diagnostics Standard

Status diagnostics должны показывать operational failures отдельно от documentation recommendations.

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
- `mcp` - stdio MCP tool listing and healthcheck;
- `codebase-memory` - optional binary/version, local cache и indexed code graphs;
- `watcher` - heartbeat and child process state.

## Required Vs Optional

Required components define `DOWN`. Optional components can define `DEGRADED`.

`codebase-memory` является optional: отсутствующий binary, недоступный CLI или отсутствие графов дает warning/`DEGRADED`, но не `DOWN`.

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
