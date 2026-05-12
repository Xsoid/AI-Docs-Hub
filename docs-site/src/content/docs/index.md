---
title: AI Docs Hub
description: Local documentation hub for docs-as-code, llms.txt, RAG, and MCP access.
---

AI Docs Hub is a local infrastructure hub. It reads documentation from connected project roots, builds derived indexes, generates LLM context files, and exposes project knowledge through MCP tools.

The project documentation source of truth stays inside each project. The hub stores configuration, generated artifacts, indexes, templates, and ecosystem-level documentation.

## Layers

- Docs-as-code layer: project documentation remains in the project repository.
- llms.txt layer: generated machine-readable Markdown context files.
- Lite RAG layer: local index in `storage/index`.
- MCP bridge layer: stdio tools for Codex and other local agents.
- Agent rules layer: namespace and safety policies.

