# 2026-10-05: Context Freshness Snapshots

Добавлен deterministic freshness-контур для project context:

- `get_project_context` теперь возвращает `context_fingerprint`;
- MCP tools `capture_project_context` и `check_project_context` создают и проверяют project-scoped snapshots;
- fingerprints учитывают Git HEAD/working patch, normalized project config, instruction и skill hashes, а также docs-index source/content hashes;
- snapshots сохраняются атомарно в ignored `storage/context-snapshots/<project>/` и содержат только metadata/digests;
- freshness явно различает `fresh`, `stale`, `degraded` и `missing`, а недоступный Codebase Memory не подменяется ложным `fresh`;
- добавлены проверки deterministic identity, Git/config/instruction/index/skill changes, timestamp-only reindex, project isolation и отсутствие source content/raw diff в snapshot.

Документация обновлена в architecture, MCP policy и project lifecycle references.
