# AI Docs Hub Agent Rules

This repository is the local AI Docs Hub. It stores infrastructure, generated artifacts, templates, indexes, and ecosystem-level documentation. Project-specific documentation must stay inside each connected project.

## Non-Negotiable Documentation Rule

Hub documentation is part of the implementation. This rule must never be ignored.

Any AI Docs Hub change that affects architecture, RAG, MCP, docs-site, indexing, generated context, project config behavior, runtime, operations, stack dependencies, commands, status fields, or agent workflow must update the source documentation in `docs/` and the matching docs-site content in `docs-site/src/content/docs/` in the same change.

If the behavior affects usage, operations, debugging, or extension, the same change must also add a change note in `docs/changes/`.

Do not finish a hub change by leaving documentation as a follow-up. If the documentation cannot be updated in the same change, stop and report that the implementation is incomplete.

Before changing RAG, MCP, docs-site, indexing, or generated context behavior:

1. Read the architecture docs in `docs-site/src/content/docs/hub/architecture.md`.
2. Read the relevant policy docs in `docs-site/src/content/docs/standards/`.
3. Keep project namespaces isolated.
4. Never index `.env`, private keys, credentials, tokens, cookies, sessions, dumps, or secret-looking files.
5. Treat connected projects as read-only unless the user explicitly asks for edits in that project.
6. Global `~/.codex/config.toml` may be edited when the task requires Codex or MCP setup; keep those edits scoped and report them.
7. If documentation and code conflict, report the conflict with source paths instead of hiding it.
8. If project context is not found, say that the search returned no matching context.
9. Remember that docs-as-code is the source of truth. RAG indexes and `llms*.txt` files are derived artifacts.
10. Do not leave hub documentation as a follow-up when the current change creates a new concept, command, status field, stack dependency, or operational workflow.

Do not mix context from different projects unless the user directly asks for cross-project analysis.
