---
title: Usage
description: Core commands for setup, docs, llms, RAG, and MCP.
---

Run setup:

```sh
make setup
```

Setup expects local Python 3.11 and Node.js 22 LTS with npm. See [Autonomous Setup](/hub/autonomous-setup/).

Start the docs site:

```sh
make docs-dev
```

Generate LLM context files:

```sh
make llms
```

Regenerate docs-site project entries:

```sh
make project-pages
```

Validate project configs and documentation readiness:

```sh
make validate-configs
make lint PROJECT=example-project
```

Plan or create missing recommended project docs:

```sh
make scaffold-docs PROJECT=example-project
make scaffold-docs-write PROJECT=example-project
```

The first command is dry-run. The second command writes missing starter files into the connected project root.

For projects with MkDocs, keep `docs_backend: auto` in `configs/projects/*.yaml` unless you need to force `mkdocs` or `standard`.

The local status page at `/status/` includes a MkDocs component with per-project backend, config detection, adapter state, and `docs_dir`.

Index one project:

```sh
make index PROJECT=example-project
```

Watch one project and automatically reindex changed docs:

```sh
make watch PROJECT=example-project
```

Run the MCP server:

```sh
make mcp-dev
```

Run checks:

```sh
make healthcheck
make mcp-test
```
