# AI Docs Hub Agent Rules

This repository is the local AI Docs Hub. It stores infrastructure, generated artifacts, templates, indexes, and ecosystem-level documentation. Project-specific documentation must stay inside each connected project.

Before changing RAG, MCP, docs-site, indexing, or generated context behavior:

1. Read the architecture docs in `docs-site/src/content/docs/hub/architecture.md`.
2. Read the relevant policy docs in `docs-site/src/content/docs/standards/`.
3. Keep project namespaces isolated.
4. Never index `.env`, private keys, credentials, tokens, cookies, sessions, dumps, or secret-looking files.
5. Treat connected projects as read-only unless the user explicitly asks for edits in that project.
6. Do not change global `~/.codex/config.toml` without explicit confirmation.
7. If documentation and code conflict, report the conflict with source paths instead of hiding it.
8. If project context is not found, say that the search returned no matching context.
9. Remember that docs-as-code is the source of truth. RAG indexes and `llms*.txt` files are derived artifacts.

Do not mix context from different projects unless the user directly asks for cross-project analysis.

