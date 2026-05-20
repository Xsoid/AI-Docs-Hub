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

## Standards catalog

The hub currently uses these standards:

- Documentation standard: docs-as-code ownership, required project docs, hub documentation duty, change notes, generated files, path portability, and secret hygiene.
- [RAG Policy](/standards/rag-policy/): project namespaces, local indexing, secret-safe source filtering, search output metadata, watch mode, and RAG freshness diagnostics.
- [MCP Policy](/standards/mcp-policy/): stdio JSON-RPC behavior, project scoping, stderr logging, confirmation for project-file writes, and scoped Codex config edits.
- [llms.txt](/standards/llms-txt/): generated LLM context files, input sources, and manual-edit restrictions.
- Runtime standard: local Python 3.11, Node.js 22/npm 10, optional macOS `launchd`, foreground `hub-dev`, status endpoint, and local storage.
- Project config standard: portable roots, isolated namespaces, `sources`, `include`, `exclude`, `agent_rules`, `docs_backend`, and `mkdocs_config`.
- Source discovery standard: manual include/exclude rules are combined with safe MkDocs structural discovery when enabled.
- Status diagnostics standard: `/status/` should expose global health and project-scoped diagnostics for projects, generated context, RAG, MkDocs, and documentation readiness.
- Scaffold standard: documentation scaffold is dry-run by default, writes only after explicit confirmation, and never overwrites non-empty project files.
- Security standard: secret-looking files and content must be excluded from indexing and generated context.

If a new hub behavior does not fit one of these standards, add or extend a standards section before treating the behavior as established.

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

## Project config

Project configs live in `configs/projects/*.yaml` and must keep project context isolated:

- `project` and `namespace` identify the project scope;
- `root` should use a portable path such as `${AI_DOCS_PROJECTS_ROOT}/project-name`;
- `sources`, `include`, and `exclude` define the readable surface;
- `agent_rules` carry project-specific instructions into profiles;
- `docs_backend` must be `auto`, `standard`, or `mkdocs`;
- `mkdocs_config` must be relative to the project root.

Placeholder sample configs may exist, but real project configs should resolve to an existing directory.

## MkDocs

MkDocs is supported as a read-only source adapter:

- `docs_backend: auto` uses `mkdocs.yml` or `mkdocs.yaml` when present.
- `docs_backend: mkdocs` expects MkDocs, but falls back to normal `include` rules if the config is missing.
- `docs_backend: standard` ignores MkDocs.

The hub reads structural fields such as `site_name`, `docs_dir`, `site_dir`, `nav`, `exclude_docs`, `draft_docs`, `not_in_nav`, and simple `INHERIT`. It does not execute MkDocs plugins, hooks, Python code, or Markdown extensions.

## Runtime and status

The hub runtime is local-first:

- Python 3.11 runs scripts, Lite RAG, MCP, healthcheck, indexing, scaffold, watcher, and generated context workflows.
- Node.js 22/npm 10 runs Astro Starlight docs-site.
- `scripts/hub-dev` runs docs-site and watcher in foreground.
- macOS `launchd` may run the same supervisor persistently.
- `/status/` exposes global health plus project-scoped diagnostics where useful.

Status diagnostics should separate operational failures from recommendations. Documentation readiness gaps are recommendations; stale or missing RAG indexes and missing generated artifacts are operational warnings.

## Generated artifacts

Generated artifacts are derived from docs-as-code and configs:

- `storage/index/*.json`;
- `storage/generated/*`;
- `docs-site/public/llms*.txt`;
- `docs-site/src/content/docs/projects/*`;
- `docs-site/dist/`;
- runtime heartbeat and log files under `storage/runtime` and `storage/logs`.

Do not edit generated artifacts manually as source documentation.

## Path portability

Source docs and committed configs should avoid hard-coded machine-specific absolute paths.

Use:

- `${AI_DOCS_PROJECTS_ROOT}/project-name` for connected project roots;
- `<EXTERNAL_PROJECT_ROOT>` for examples;
- `<AI_DOCS_HUB_ROOT>` for command examples;
- generated host-specific absolute paths only in runtime files outside source-of-truth.

## HTML

The docs site uses Astro Starlight. Starlight provides semantic documentation pages with page navigation, main content landmarks, article content, headings, and accessible navigation behavior by default.
