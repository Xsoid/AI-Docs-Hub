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
    architecture/
    modules/
    decisions/
    api/
    deployment/
    glossary.md
```

The hub may create derived generated views, but the source of truth stays in the project.

## HTML

The docs site uses Astro Starlight. Starlight provides semantic documentation pages with page navigation, main content landmarks, article content, headings, and accessible navigation behavior by default.

