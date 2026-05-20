---
title: Agent Rules
description: Rules for agents using the hub.
---

- Do not mix namespaces between projects unless the user explicitly asks for cross-project context.
- Do not index files that look like secrets, credentials, tokens, cookies, sessions, private keys, or dumps.
- Do not change connected project files from the hub workflow.
- Global Codex config may be edited when the task requires Codex or MCP setup; keep edits scoped and report them.
- If documentation and code conflict, report the conflict with source paths.
- If project context is missing, say that no matching context was found.
- Treat RAG output as an index over docs-as-code, not as the source of truth.
- Treat hub documentation as part of the implementation: update `docs/`, docs-site content, and `docs/changes/` whenever a hub change affects architecture, RAG, MCP, docs-site, indexing, generated context, runtime, operations, project config behavior, or agent workflow.
