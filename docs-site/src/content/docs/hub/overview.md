---
title: Overview
description: What the local AI Docs Hub owns and what it does not own.
---

The hub is a local coordination layer for multiple projects. It should not become a manual copy of every project knowledge base.

Project-level documentation belongs in the project:

- `AGENTS.md`
- `README.md`
- `docs/architecture`
- `docs/modules`
- `docs/decisions`
- `docs/api`
- `docs/deployment`
- `docs/glossary.md`

The hub owns infrastructure:

- project connection configs;
- local indexes and generated files;
- MCP bridge;
- docs-site;
- shared templates;
- shared agent policies.

## Local-first

The default implementation does not send project contents to external APIs, does not use cloud vector databases, and does not edit connected projects.

