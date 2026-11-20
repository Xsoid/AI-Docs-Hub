# Подключение Kimi Code

Hub поддерживает трёх агентских клиентов: Codex, Claude Code и Kimi Code. Все клиенты используют одни и те же MCP servers, project scope, confirmation rules и Project Lifecycle gate. Различается только место регистрации MCP servers.

| Клиент | Регистрация MCP | Команда Hub |
| --- | --- | --- |
| Codex | `~/.codex/config.toml` | точечная правка; Codebase Memory через `codebase-memory.index` |
| Claude Code | local scope в `~/.claude.json` | `scripts/claude-mcp` |
| Kimi Code | user-level `~/.kimi-code/mcp.json` | `scripts/kimi-mcp` |

## Регистрация

Kimi Code хранит MCP servers в `mcp.json`: user-level файл `$KIMI_CODE_HOME/mcp.json` или `~/.kimi-code/mcp.json` действует для всех проектов, project-level `.kimi-code/mcp.json` — только для текущего репозитория. Hub регистрирует servers только на user level и не пишет `.kimi-code/mcp.json` в подключенный проект: connected projects остаются read-only.

Проверка без записи:

    python3.11 scripts/kimi-mcp status --project name
    python3.11 scripts/kimi-mcp configure --project name

Запись:

    make kimi-mcp-install PROJECT=name
    make kimi-mcp-install-hub
    python3.11 scripts/kimi-mcp configure --all --write

Для подключенного проекта команда регистрирует:

- `<project>_docs` — `mcp/server.py --project <project>`;
- `codebase_<project>` — `mcp/codebase_memory_proxy.py --project <project>`, только если установлен binary Codebase Memory и построен graph проекта.

Для checkout Hub `--hub` регистрирует unscoped `local_ai_docs_hub` без `--project`: все project-scoped tools принимают project явным аргументом. Это рекомендуемый вариант для Kimi Code, потому что user-level config один на все проекты, а каждый server добавляет свой набор tools в контекст сессии. Checkout Hub нельзя зарегистрировать как подключенный проект.

Так как user-level `mcp.json` один на машину, entries всех проектов и unscoped Hub server лежат в одном файле и не мешают друг другу: команды проекта управляют только своими именами (`<project>_docs`, `codebase_<project>`).

## Правила Записи

- Default mode — dry-run. Он показывает текущее состояние и список `changes`. Запись выполняется только с `--write`.
- Команда меняет только ключ `mcpServers` в user-level `mcp.json`. Остальные ключи файла сохраняются.
- Hub-managed entry определяется по пути к `mcp/server.py` или `mcp/codebase_memory_proxy.py` этого checkout. Entry с тем же именем, но с другим command path, получает статус `foreign` и не перезаписывается.
- `remove` удаляет только Hub-managed entries выбранной цели. Entries других проектов и unscoped Hub server не затрагиваются.
- Файл перечитывается непосредственно перед записью и заменяется атомарно с сохранением прав доступа. Невалидный JSON блокирует запись.
- Вывод команды содержит только имена servers, статусы и путь к config. Содержимое `mcp.json` не выводится.

Если `restart_required=true`, начните новую сессию Kimi Code. Уже открытая сессия не загружает новые MCP servers; статус подключения показывает команда `/mcp`.

## Review Workflow

Kimi Code проходит тот же gate, что и Codex: [Project Lifecycle](project-lifecycle.md). Code review выполняется в сессии Kimi Code по точному scope. Результат записывается MCP tool `record_code_review` или `record_security_review`. Если MCP недоступен, используйте `scripts/project-lifecycle record-review`.
