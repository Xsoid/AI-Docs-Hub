# AI Docs Hub Agent Rules

AI Docs Hub stores local infrastructure, templates, generated artifacts, indexes, and ecosystem documentation. Documentation for a connected project stays in that project.

## Required Boundaries

- Work in `main`. Do not create a feature, task, or agent branch unless the user explicitly requests it.
- Keep connected-project namespaces separate. Treat connected projects as read-only unless the user explicitly authorizes a write.
- Do not index, commit, quote, or copy `.env`, keys, credentials, tokens, cookies, sessions, dumps, secret-looking files, or project-derived content into tracked Hub files.
- Keep `configs/projects/`, `storage/`, generated pages, and `llms*.txt` local and ignored. Docs-as-code is the source; indexes and generated context are derived artifacts.
- A scoped edit to `~/.codex/config.toml` is permitted only when Codex or MCP setup requires it. Report that edit.

## Documentation Duty

Documentation is part of every Hub implementation. For a change to architecture, RAG, MCP, docs-site, indexing, generated context, runtime, operations, dependencies, commands, status fields, project-config behavior, or agent workflow, update the canonical document in `docs/` in the same change. Add a note in `docs/changes/` when the change affects use, operations, debugging, or extension.

Do not manually edit pages marked as generated. Run `make hub-pages` to render canonical Hub documentation into the docs site. Hand-authored site-only pages may change only for unique site navigation or presentation; they must link to the canonical rule instead of restating it. If code and documentation conflict, report both paths and resolve the conflict.

## Repository Map

| Area | Canonical documentation |
| --- | --- |
| `configs/projects/` | `docs/standards/project-config.md` |
| `rag/` | `docs/standards/rag-policy.md` |
| `mcp/` | `docs/standards/mcp-policy.md` |
| `docs-site/`, `storage/` | `docs/standards/generated-artifacts.md` |
| `scripts/`, `Makefile` | `docs/operations/command-reference.md` |
| `templates/` | `docs/standards/scaffold.md` |
| `docs/` | `docs/README.md` |

Read `docs/architecture/overview.md` before changing architecture, RAG, MCP, docs-site, indexing, or generated context. Read the applicable document in `docs/standards/` before changing its policy.

## Agent Workflow Routing

For every code change, use these procedures in order. They own the workflow details and the current patch-fingerprint requirements:

1. `.agents/skills/code-change-verification/SKILL.md`
2. `.agents/skills/code-review/SKILL.md`
3. `.agents/skills/security-review/SKILL.md`
4. `.agents/skills/pre-publish/SKILL.md`

Use `docs/standards/documentation-hygiene.md` for document ownership and `docs/standards/technical-writing.md` for writing style. Do not copy those rules into this file.
