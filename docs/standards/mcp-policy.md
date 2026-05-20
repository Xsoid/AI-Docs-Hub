# MCP Policy

MCP bridge работает как локальный stdio JSON-RPC server.

## Runtime

```sh
python3.11 mcp/server.py
python3.11 mcp/server.py --project project-name
```

Stdout зарезервирован для MCP JSON-RPC messages. Logs должны идти в stderr.

## Scope

- Без `--project` каждый tool call должен явно передавать `project`, если tool project-scoped.
- С `--project` server фиксирует active project и отклоняет попытки вызвать другой project.
- Tools не должны смешивать namespaces между проектами.

## Tools

Текущий набор:

- `list_projects`;
- `get_project_profile`;
- `search_docs`;
- `read_doc`;
- `search_decisions`;
- `search_modules`;
- `index_project`;
- `healthcheck`;
- `lint_project`;
- `scaffold_project_docs`;
- `read_operation_log`.

## Confirmation Rules

`index_project` не запускает indexing без `confirm=true`. Safe default возвращает risk, command и пример MCP call.

`scaffold_project_docs` не пишет files в connected project root без `confirm=true`. Dry-run остается default.

## Config Edits

Global `~/.codex/config.toml` можно редактировать только когда задача требует Codex/MCP setup. Правки должны быть scoped и явно описаны пользователю.

Project files считаются read-only, кроме явных scaffold write workflows.
