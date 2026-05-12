---
title: Usage
description: Core commands for setup, docs, llms, RAG, and MCP.
---

Run setup:

```sh
make setup
```

Start the docs site:

```sh
make docs-dev
```

Generate LLM context files:

```sh
make llms
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

If local Node is missing, the docs commands use the official `node:22-alpine` Docker image.
