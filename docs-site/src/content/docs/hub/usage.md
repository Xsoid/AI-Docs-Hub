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
