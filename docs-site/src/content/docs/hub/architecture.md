---
title: Architecture
description: Layered architecture of the local AI Docs Hub.
---

The hub is split into independent layers.

## Stack Map

AI Docs Hub is a local multi-stack toolchain. Each stack has a narrow responsibility:

- Python 3.11: operational scripts, project config loading, Lite RAG, MCP stdio server, healthcheck, status API source data, watcher, documentation scaffold, secret scanning, generated project pages, and `llms*.txt` generation.
- Node.js 22 LTS with npm 10: docs-site runtime and build pipeline.
- Astro 6 and Starlight: documentation website, `/status/` page shell, navigation, search index build, and content rendering from `docs-site/src/content/docs/`.
- Markdown docs-as-code: hub source documentation in `docs/`, docs-site source pages in `docs-site/src/content/docs/`, and project source documentation inside each connected project.
- YAML project config: `configs/projects/*.yaml` defines project roots, namespaces, source include/exclude rules, agent rules, and docs backend mode.
- MkDocs adapter: read-only structural discovery for projects with `mkdocs.yml` or `mkdocs.yaml`; it never runs MkDocs plugins, hooks, Python code, or Markdown extensions.
- Lite JSON/BM25 RAG: local indexing and search over allowed project documentation, stored under `storage/index`.
- MCP stdio bridge: `mcp/server.py` exposes project-scoped tools to Codex and other MCP clients over JSON-RPC stdio.
- Local runtime: `scripts/hub-dev` supervises docs-site and watcher in foreground; macOS `launchd` can run the same supervisor persistently.
- macOS menu bar app: optional Swift/AppKit wrapper built by `scripts/hub-menubar`; it is an operational convenience, not a source of truth.
- Generated artifacts: `storage/generated`, `docs-site/public/llms*.txt`, `docs-site/src/content/docs/projects/*`, runtime heartbeats, logs, and indexes are derived from docs-as-code and configs.

Docker, RAGFlow, external vector databases, cloud search, and remote LLM APIs are outside the default working stack.

## Docs-as-code

Project docs remain in their own project roots. The hub reads them through YAML configs in `configs/projects`.

Project configs build an effective source plan before indexing. The default `docs_backend: auto` uses normal `sources`, `include`, and `exclude` rules, and safely reads `mkdocs.yml` or `mkdocs.yaml` when a connected project has one. MkDocs support is read-only: the hub reads structural fields such as `docs_dir`, `site_dir`, `nav`, `exclude_docs`, and `draft_docs`, but does not execute plugins, hooks, or Markdown extensions.

The local `/status/` page exposes project-scoped diagnostics where that is useful: project config/source discovery, generated project pages, RAG index state, MkDocs adapter state, documentation readiness, and scaffold availability.

## llms.txt

`scripts/generate-llms` builds:

- `docs-site/public/llms.txt`
- `docs-site/public/llms-full.txt`
- `docs-site/public/llms-small.txt`
- mirrored copies in `storage/generated`

These files are generated artifacts and must not be edited manually.

## Lite RAG

The default RAG backend is local and lightweight. It reads project configs, filters allowed files, scans for secrets, chunks content, and writes JSON indexes under `storage/index`.

If `docs_backend: mkdocs` is requested and the MkDocs config is missing, indexing falls back to configured include patterns and reports a warning instead of failing only because `mkdocs.yml` is absent.

The status page reports RAG backend, source file count, indexed document count, chunk count, index path, indexed timestamp, newest source timestamp, and freshness per project. A stale index is an operational warning.

## Documentation Scaffold

`scripts/scaffold-project-docs` can create missing recommended documentation files in a connected project. It is dry-run by default. Writing project files requires `--write`, `make scaffold-docs-write`, or MCP `scaffold_project_docs` with `confirm=true`.

Documentation readiness reports coverage percent for core and technical docs. Scaffold reports coverage before and after planned or executed changes.

## MCP Bridge

`mcp/server.py` is a stdio MCP server. It exposes project-scoped tools for listing projects, searching docs, reading sources, and checking health.

## Runtime

The default runtime is fully local: Python 3.11, Node.js 22 LTS with npm, and local filesystem storage. Docker, external vector databases, and RAGFlow are not part of the working architecture.
