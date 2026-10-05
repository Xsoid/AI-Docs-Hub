# Project Context Manifest

## Что изменилось

- Добавлены MCP tools `get_project_context` и `read_project_instruction`.
- Manifest агрегирует существующие project config, Lite RAG index/readiness, Skill Intelligence и quality profile без дублирования их business logic.
- Root и nested `AGENTS.md`/`CLAUDE.md` обнаруживаются bounded и deterministic; manifest возвращает только metadata и hashes.
- Instruction content читается только on-demand по ранее обнаруженному project-relative path, с containment, excludes, secret scan и byte limit.

## Проверка

- Добавлены тесты instruction discovery, symlink escape, excluded directories, deterministic ordering, bounded result, secret blocking, skills metadata, missing index и MCP project isolation.
- MCP remains read-only and project-scoped; no shell, editing, worktree or subagent behavior was added.
