# Generated-Артефакты

Generated-артефакт нельзя редактировать вручную. Измените его канонический вход или генератор, затем выполните генерацию.

| Артефакт | Канонический источник | Генератор | Хранение |
| --- | --- | --- | --- |
| Hub architecture, operations и standards pages | `docs/architecture/`, `docs/operations/`, `docs/standards/` | `scripts/generate-hub-pages` | ignored `docs-site/src/content/docs/hub/` и `standards/` |
| Project overview pages | local project config, index и readiness metadata | `scripts/generate-project-pages` | ignored `docs-site/src/content/docs/projects/` |
| `llms*.txt` | canonical docs и allowed project metadata | `scripts/generate-llms` | ignored `docs-site/public/` и `storage/generated/` |
| Indexes, reports и runtime state | local runtime inputs | runtime scripts | ignored `storage/` |

`docs-site/src/content/docs/index.md` and the tracked pages in `hub/` are site-only entry pages. They can contain route-specific navigation and short descriptions. They must link to canonical `docs/` content for rules and procedures.

Run `make hub-pages` after a Hub-documentation change. The generator fails before an output collision or a non-generated page overwrite. It removes only obsolete pages that contain its marker and are inside managed Hub or standards directories.
