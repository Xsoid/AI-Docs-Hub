---
title: MCP Policy
description: MCP bridge behavior and safety constraints.
---

The MCP bridge runs as a local stdio server.

Rules:

- stdout is reserved for MCP JSON-RPC messages;
- logs go to stderr;
- tools are project-scoped;
- risky or long operations must be described explicitly;
- global Codex config may be edited for requested Codex/MCP setup; edits must stay scoped and be reported;
- project files are read by default and are not edited by the hub.

Project-file write tools must require explicit confirmation. For example, documentation scaffold must return a safe dry-run response unless `confirm=true` is provided.
