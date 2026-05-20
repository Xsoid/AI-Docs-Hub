---
title: Status Diagnostics
description: hub-status components, required checks and JSON contract.
---

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
- `watcher` - heartbeat and child process state.

## Required Vs Optional

Required components define `DOWN`. Optional components can define `DEGRADED`.

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

Dashboard должен использовать этот endpoint как source data и не выполнять destructive actions.
