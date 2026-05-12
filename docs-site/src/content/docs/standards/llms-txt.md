---
title: llms.txt
description: Policy for generated LLM context files.
---

`llms.txt`, `llms-full.txt`, and `llms-small.txt` are generated artifacts.

They are produced by:

```sh
make llms
```

Generation reads:

- hub docs in `docs-site/src/content/docs`;
- configured project docs from valid `configs/projects/*.yaml`;
- only files allowed by each project config.

Do not edit generated `llms*.txt` files manually.

