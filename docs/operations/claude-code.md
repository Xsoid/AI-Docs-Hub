# Подключение Claude Code

Hub поддерживает два агентских клиента: Codex и Claude Code. Оба клиента используют одни и те же MCP servers, project scope, confirmation rules и Project Lifecycle gate. Различается только место регистрации MCP servers.

| Клиент | Регистрация MCP | Команда Hub |
| --- | --- | --- |
| Codex | `~/.codex/config.toml` | точечная правка; Codebase Memory через `codebase-memory.index` |
| Claude Code | local scope в `~/.claude.json` | `scripts/claude-mcp` |

## Регистрация

Claude Code хранит local-scope MCP servers в `~/.claude.json` под ключом `projects.<project dir>.mcpServers`. Если задана переменная `CLAUDE_CONFIG_DIR`, используется `$CLAUDE_CONFIG_DIR/.claude.json`. Hub не пишет `.mcp.json` в подключенный проект и не меняет tracked-файлы проекта.

Проверка без записи:

    python3.11 scripts/claude-mcp status --project name
    python3.11 scripts/claude-mcp configure --project name

Запись:

    make claude-mcp-install PROJECT=name
    make claude-mcp-install-hub
    python3.11 scripts/claude-mcp configure --all --write

Для подключенного проекта команда регистрирует:

- `<project>_docs` — `mcp/server.py --project <project>`;
- `codebase_<project>` — `mcp/codebase_memory_proxy.py --project <project>`, только если установлен binary Codebase Memory и построен graph проекта.

Для checkout Hub `--hub` регистрирует unscoped `local_ai_docs_hub`. Checkout Hub нельзя зарегистрировать как подключенный проект.

## Правила Записи

- Default mode — dry-run. Он показывает текущее состояние и список `changes`. Запись выполняется только с `--write`.
- Команда меняет только `mcpServers` выбранного project dir. Остальные ключи `~/.claude.json` сохраняются.
- Hub-managed entry определяется по пути к `mcp/server.py` или `mcp/codebase_memory_proxy.py` этого checkout. Entry с тем же именем, но с другим command path, получает статус `foreign` и не перезаписывается.
- `remove` удаляет только Hub-managed entries.
- Файл перечитывается непосредственно перед записью и заменяется атомарно с сохранением прав доступа. Невалидный JSON блокирует запись.
- Вывод команды содержит только имена servers, статусы и project dir. Содержимое `~/.claude.json` не выводится.

Если `restart_required=true`, перезапустите сессию Claude Code. Открытая сессия не загружает новые MCP servers.

Ключ project dir — абсолютный путь корня проекта. Сессия Claude Code в git worktree использует другой путь и не получает эти servers.

## Review Workflow

Claude Code проходит тот же gate, что и Codex: [Project Lifecycle](project-lifecycle.md). Code review выполняется в сессии Claude Code по точному scope. Результат записывается MCP tool `record_code_review` или `record_security_review`. Если MCP недоступен, используйте `scripts/project-lifecycle record-review`.
