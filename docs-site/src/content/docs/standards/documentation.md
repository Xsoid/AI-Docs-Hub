---
title: Documentation Standard
description: Required project documentation structure.
---

Each connected project should keep project-specific knowledge in its own repository.

Recommended structure:

```text
project-root/
  AGENTS.md
  README.md
  docs/
    index.md
    architecture/
    modules/
    decisions/
    api/
    deployment/
    operations/
    infrastructure/
    configuration.md
    security.md
    data.md
    integrations.md
    observability.md
    testing.md
    troubleshooting.md
    development.md
    glossary.md
```

The hub may create derived generated views, but the source of truth stays in the project.

## Hub documentation duty

Hub documentation is part of the implementation, not a follow-up. Any hub change that introduces or changes architecture, RAG behavior, MCP tools, docs-site behavior, indexing rules, generated context, runtime commands, launch/supervision behavior, project config behavior, agent workflow, stack dependencies, or operational workflows must update source docs in `docs/`, the matching docs-site page under `docs-site/src/content/docs/`, and a `docs/changes/` note when the behavior affects usage, operations, debugging, or extension.

## Documentation readiness

The hub should nudge each connected project toward a complete documentation set without blocking search when docs are still incomplete.

Recommended project docs:

- `README.md`
- `AGENTS.md`
- `docs/index.md`
- `docs/architecture/`
- `docs/modules/`
- `docs/decisions/`
- `docs/api/`
- `docs/deployment/`
- `docs/operations/`
- `docs/infrastructure/`
- `docs/configuration.md`
- `docs/security.md`
- `docs/data.md`
- `docs/integrations.md`
- `docs/observability.md`
- `docs/testing.md`
- `docs/troubleshooting.md`
- `docs/development.md`
- `docs/glossary.md`

If a project uses MkDocs, the `docs_dir` from `mkdocs.yml` is used as the documentation root for these recommendations.

Missing or empty sections are documentation readiness recommendations, not config errors. Readiness reports include a documentation coverage percentage and category-level coverage for core and technical docs.

Documentation readiness recommendations are not operational health failures. They remain visible in `healthcheck` and project profiles, but they should not make repository/runtime status `degraded` unless there are real config warnings or errors.

## Documentation scaffold

The hub can plan or create starter files for missing recommended docs:

```sh
make scaffold-docs PROJECT=example-project
make scaffold-docs-write PROJECT=example-project
```

Rules:

- `scaffold-docs` is dry-run and does not change the connected project.
- `scaffold-docs-write` is explicit permission to write missing docs files into the project root.
- The MCP scaffold tool must require `confirm=true`.
- Non-empty files must not be overwritten.
- Empty recommended files may be filled from templates unless disabled.
- Templates must not contain secrets or host-specific values.

## MkDocs

MkDocs is supported as a read-only source adapter:

- `docs_backend: auto` uses `mkdocs.yml` or `mkdocs.yaml` when present.
- `docs_backend: mkdocs` expects MkDocs, but falls back to normal `include` rules if the config is missing.
- `docs_backend: standard` ignores MkDocs.

The hub reads structural fields such as `site_name`, `docs_dir`, `site_dir`, `nav`, `exclude_docs`, `draft_docs`, `not_in_nav`, and simple `INHERIT`. It does not execute MkDocs plugins, hooks, Python code, or Markdown extensions.

## HTML

The docs site uses Astro Starlight. Starlight provides semantic documentation pages with page navigation, main content landmarks, article content, headings, and accessible navigation behavior by default.
