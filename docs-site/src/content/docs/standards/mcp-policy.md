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
- global Codex config is never changed automatically;
- project files are read by default and are not edited by the hub.

