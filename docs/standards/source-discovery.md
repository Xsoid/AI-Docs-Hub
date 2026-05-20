# Source Discovery Standard

Source discovery строит effective source plan для каждого connected project.

## Pipeline

1. Load `configs/projects/*.yaml`.
2. Resolve portable `root`.
3. Read `sources`, `include` и `exclude`.
4. Apply MkDocs adapter, если `docs_backend` это разрешает.
5. Deduplicate sources/include/exclude.
6. Apply path safety and exclude rules.
7. Run secret scan before indexing or generated context.

## MkDocs Adapter

Adapter read-only. Он может читать:

- `site_name`;
- `docs_dir`;
- `site_dir`;
- `nav`;
- `exclude_docs`;
- `draft_docs`;
- `not_in_nav`;
- простой `INHERIT`.

Adapter не выполняет:

- MkDocs plugins;
- hooks;
- Python code;
- Markdown extensions;
- `mkdocs build`.

## Status

`hub-status` и `/status/` показывают по проектам:

- configured backend;
- requested/detected/enabled MkDocs state;
- config path;
- docs_dir;
- site_dir;
- warnings;
- effective include/exclude counts.

Если source discovery не находит контекст, агент должен сказать, что search returned no matching context.
