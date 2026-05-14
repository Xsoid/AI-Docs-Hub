---
title: Architecture
description: Layered architecture of the local AI Docs Hub.
---

The hub is split into independent layers.

## Docs-as-code

Project docs remain in their own project roots. The hub reads them through YAML configs in `configs/projects`.

## llms.txt

`scripts/generate-llms` builds:

- `docs-site/public/llms.txt`
- `docs-site/public/llms-full.txt`
- `docs-site/public/llms-small.txt`
- mirrored copies in `storage/generated`

These files are generated artifacts and must not be edited manually.

## Lite RAG

The default RAG backend is local and lightweight. It reads project configs, filters allowed files, scans for secrets, chunks content, and writes JSON indexes under `storage/index`.

## MCP Bridge

`mcp/server.py` is a stdio MCP server. It exposes project-scoped tools for listing projects, searching docs, reading sources, and checking health.

## Runtime

The default runtime is fully local: Python 3.11, Node.js 22 LTS with npm, and local filesystem storage. Docker, external vector databases, and RAGFlow are not part of the working architecture.
