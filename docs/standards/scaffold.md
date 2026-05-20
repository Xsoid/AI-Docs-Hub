# Scaffold Standard

Documentation scaffold помогает подключенному проекту добрать recommended docs, но project files остаются read-only по умолчанию.

## Dry-Run

```sh
make scaffold-docs PROJECT=project-name
```

Показывает planned actions и не пишет project files.

## Write Mode

```sh
make scaffold-docs-write PROJECT=project-name
```

Это явное разрешение на запись в connected project root.

Rules:

- create missing directories;
- create missing files from templates;
- optionally fill empty recommended files;
- never overwrite non-empty files;
- keep templates secret-free and host-agnostic.

## MCP

`scaffold_project_docs` обязан требовать:

```json
{"confirm": true}
```

Без confirmation tool возвращает risk, safe default, dry-run command и write command.

## Coverage

Scaffold reports:

- coverage before;
- coverage after;
- actions count;
- written count;
- remaining recommendations.
