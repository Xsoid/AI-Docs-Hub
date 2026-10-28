# Generated-Артефакты

Generated-артефакт нельзя редактировать вручную. Измените его канонический вход или генератор, затем выполните генерацию.

| Артефакт | Канонический источник | Генератор | Хранение |
| --- | --- | --- | --- |
| Hub architecture, operations и standards pages | `docs/architecture/`, `docs/operations/`, `docs/standards/` | `scripts/generate-hub-pages` | ignored `docs-site/src/content/docs/hub/` и `standards/` |
| Project overview pages | local project config, index и readiness metadata | `scripts/generate-project-pages` | ignored `docs-site/src/content/docs/projects/` |
| `llms*.txt` | canonical docs и allowed project metadata | `scripts/generate-llms` | ignored `docs-site/public/` и `storage/generated/` |
| Indexes, reports и runtime state | local runtime inputs | runtime scripts | ignored `storage/` |

`rag/config.py` owns the storage root as `STORAGE_DIR`. Every `storage/` path in `rag/` and `scripts/generate-llms` derives from it. The `HUB_STORAGE_DIR` environment variable moves the root, and `make test` uses it to give the test suite a temporary storage directory. `MCP_AUDIT_DIR` still overrides the MCP audit directory alone. An empty value means unset.

`docs-site/src/content/docs/index.md` and the tracked pages in `hub/` are site-only entry pages. They can contain route-specific navigation and short descriptions. They must link to canonical `docs/` content for rules and procedures.

Run `make hub-pages` after a Hub-documentation change. The generator fails before an output collision or a non-generated page overwrite. It removes only obsolete pages that contain its marker and are inside managed Hub or standards directories.

## Политика Хранения `storage/`

| Каталог | Содержимое | Политика хранения |
| --- | --- | --- |
| `index/` | `{project}.json` - RAG index, `{project}_log.jsonl` - operation log | index перезаписывается при индексации; operation log хранит последние 1000 записей (`MAX_OPERATION_LOG_ENTRIES`, `rag/logging.py`), старые строки удаляются при каждой записи |
| `decision-engine/{project}/` | cache решений и `metrics.json` | не более 200 cache-файлов на проект (`MAX_CACHE_FILES`) |
| `project-lifecycle/{project}/` | init, quality profile, `reviews/{fingerprint}/` | `reviews/` хранит последние 50 fingerprint на проект (`MAX_REVIEW_FINGERPRINTS`, `rag/project_lifecycle.py`). Лишние удаляются при каждой записи verification или review. Записанный fingerprint становится самым новым, поэтому review текущего patch не удаляется |
| `skill-intelligence/{project}/` | `audit.json`, `inventory.json` | перезаписываются |
| `context-snapshots/{project}/` | context snapshots | последние 50 на проект (`MAX_CONTEXT_SNAPSHOTS`, `rag/context_freshness.py`), лишние удаляются при каждом `capture_project_context` |
| `codebase-memory/` | `{project}.db` и `-shm`/`-wal`, общие `_config.db` и `logs/` | управляет Codebase Memory |
| `runtime/` | статус runtime, `codebase-memory/{project}.status.json`, `fixes/` jobs, `bin/` | статусы перезаписываются; `fixes/` хранит последние 50 job JSON (`MAX_FIX_JOBS`, `scripts/apply-fix`), лишние удаляются при создании нового job |
| `logs/` | runtime и `apply-fix` logs | ротация, см. `docs/operations/runtime-observability.md` |
| `mcp-audit/` | дневные JSONL | `MCP_AUDIT_RETENTION_DAYS`, по умолчанию 30 дней |
| `generated/` | `llms*.txt`, report | перезаписываются |

Если project config удален, его project-scoped записи остаются. `rag/storage_retention.py` перечисляет такие места (`project_locations()`):

- `index/`;
- `decision-engine/`, `project-lifecycle/`, `skill-intelligence/`, `context-snapshots/`;
- `codebase-memory/{project}.db*`;
- `runtime/codebase-memory/{project}.status.json`.

`make storage-prune` показывает такие записи и ничего не удаляет. `python3.11 scripts/storage-prune --apply` удаляет их. Без `--apply` удаления нет. Если хотя бы один project config невалиден, команда завершается ошибкой и ничего не удаляет. `make hub-status` и `/status/` показывают orphan storage как warning компонента `storage`.
