---
title: Autonomous Setup
description: Local runtime dependencies for running AI Docs Hub without Docker.
---

AI Docs Hub is designed to run as a local autonomous toolchain. It does not require Docker for docs, Lite RAG, `llms*.txt`, MCP, indexing, linting, or watch mode.

## Required Runtime

Install these tools on the host machine:

- Python 3.11 available as `python3.11`;
- Node.js 22 LTS available as `node`;
- npm 10+ available as `npm`;
- Git;
- `make`.

On macOS with Homebrew:

```sh
brew install python@3.11 node@22
brew link --force --overwrite node@22
```

`python3` on macOS can point to an older system Python. Hub commands intentionally use `python3.11`.

## Local Setup

From the hub root:

```sh
make setup
make healthcheck
make llms
make mcp-test
```

`make setup` creates `.venv`, installs docs-site npm dependencies, and validates project configs. Python dependencies are currently standard-library only.

## Runtime Roles

- Python runs Lite RAG, MCP, indexing, lint, healthcheck, `llms*.txt`, and watch mode.
- Node/npm run the Astro Starlight docs site.
- `storage/` keeps local indexes, generated files, and operation logs.
- `configs/projects/*.yaml` connects external project documentation through resolvable portable roots, such as `${AI_DOCS_PROJECTS_ROOT}/project-name`.

## Not Required

Docker is not a default runtime dependency. The hub does not require Docker Compose, RAGFlow, cloud vector databases, or external AI APIs for normal operation.

Global Codex config can be configured for MCP access. Use `codex-config.example.toml` or `project-codex-config.example.toml` as templates and keep applied edits scoped.
