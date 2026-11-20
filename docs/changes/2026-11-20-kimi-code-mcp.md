# Подключение Kimi Code К Hub

## Что Изменилось

- Новый клиент MCP-регистрации: `scripts/kimi-mcp` (`rag/kimi_code.py`) управляет Hub MCP servers в user-level `~/.kimi-code/mcp.json` (`$KIMI_CODE_HOME/mcp.json`).
- Команды зеркалируют `scripts/claude-mcp`: `status`, `configure`, `remove` с целями `--project`, `--all`, `--hub`; default — dry-run, запись только с `--write`; Makefile targets `kimi-mcp-status`, `kimi-mcp-install`, `kimi-mcp-install-hub`.
- `--hub` регистрирует unscoped `local_ai_docs_hub` — рекомендуемый вариант для Kimi Code, потому что user-level config один на все проекты.
- Общий код регистрации (имена servers, Codebase Memory availability, Hub-entry detection, atomic JSON write) вынесен в `rag/mcp_clients.py`; `rag/claude_code.py` переиспользует его без изменения поведения.
- Правила записи: изменяются только Hub-managed entries выбранной цели; entries других проектов, unscoped Hub server и чужие (`foreign`) servers не затрагиваются; невалидный JSON блокирует запись; запись атомарна с сохранением прав доступа.
- Hub не пишет project-level `.kimi-code/mcp.json` в подключенные проекты: они остаются read-only.

## Почему

Kimi Code стал третьим агентским клиентом Hub наряду с Codex и Claude Code. У Kimi Code свой формат регистрации MCP servers: единый user-level `mcp.json` с ключом `mcpServers`, где stdio server определяется полем `command` без `type`. Существующая Claude-интеграция не подходила: она пишет в `~/.claude.json` с per-project-dir scope и полем `type: "stdio"`.

## Эксплуатация

- После записи с `restart_required=true` начните новую сессию Kimi Code: открытая сессия не загружает новые MCP servers. Статус подключения показывает `/mcp`.
- `remove --project name` удаляет только entries этого проекта; unscoped Hub server удаляется через `remove --hub`.
- Процедура и правила записи: `docs/operations/kimi-code.md`; политика: `docs/standards/mcp-policy.md` (Config Edits).
- Тесты: `tests/test_kimi_code.py`; регрессия Claude-интеграции покрыта `tests/test_claude_code.py`.
