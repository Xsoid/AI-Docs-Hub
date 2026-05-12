# Agent Rules

## Project Scope

- Search only inside this project's namespace unless the user explicitly asks for cross-project context.
- Prefer `README.md`, `AGENTS.md`, and `docs/` before inferring behavior from memory.
- If documentation conflicts with code, report the conflict with both source paths.

## Safety

- Do not read or index `.env`, credentials, tokens, cookies, session files, dumps, private keys, or secret-looking files.
- Do not modify project files unless the task explicitly asks for code or documentation edits in this project.
- Do not use context from other projects without direct instruction.

## Answering

- Return source paths for claims based on project docs.
- Say clearly when project context was not found.
- Treat RAG results as derived context, not as the source of truth.

