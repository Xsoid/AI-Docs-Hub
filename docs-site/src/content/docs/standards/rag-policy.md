---
title: RAG Policy
description: Local indexing, namespace, and secret-safety policy.
---

The default RAG backend is local and stores indexes under `storage/index`.

Rules:

- every project has its own namespace;
- search is project-scoped by default;
- all indexing starts with exclude filtering and secret scanning;
- `.env`, keys, tokens, cookies, credentials, dumps, and secret-looking files are not indexed;
- RAG output must include source paths and confidence metadata;
- RAG is a derived index, not the documentation source of truth.

## Watch Mode

`scripts/watch-project` can run as a foreground local watcher:

```sh
make watch PROJECT=example-project
```

The watcher polls only configured include paths, applies exclude rules, debounces changes, runs secret scanning, updates the local project index, and regenerates `llms*.txt`.
