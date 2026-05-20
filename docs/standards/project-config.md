# Project Config Standard

Project configs живут в:

```text
configs/projects/*.yaml
```

Они описывают, какие project files хаб может читать, как изолировать namespace и какие правила передавать агентам.

## Обязательные Поля

- `project` - стабильный project id.
- `namespace` - RAG/MCP namespace.
- `root` - project root, желательно переносимый.
- `include` - allowed read surface.

## Рекомендуемые Поля

- `title` - human readable название.
- `docs_backend` - `auto`, `standard` или `mkdocs`.
- `mkdocs_config` - relative path к MkDocs config.
- `sources` - структурное описание источников.
- `exclude` - запретные paths.
- `agent_rules` - project-specific rules для agents.

## Path Portability

В committed configs нельзя hard-code absolute paths конкретной машины.

Используйте:

- `${AI_DOCS_PROJECTS_ROOT}/project-name`;
- relative path от root хаба;
- placeholder `<EXTERNAL_PROJECT_ROOT>` только для sample configs.

Host-specific absolute path допустим только во внешнем локальном config, который не коммитится.

## docs_backend

- `auto` - default; использует MkDocs structural discovery, если найден `mkdocs.yml` или `mkdocs.yaml`.
- `mkdocs` - ожидает MkDocs config; если config отсутствует, пишет warning и продолжает по include rules.
- `standard` - игнорирует MkDocs и использует только configured `sources`/`include`/`exclude`.

## Validation

```sh
make validate-configs
```

Validation отличает:

- errors: config не пригоден для indexing;
- warnings: config работает, но требует внимания;
- recommendations: documentation readiness gaps, не operational failure.
