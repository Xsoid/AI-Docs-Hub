# 2026-10-05: Sanitized MCP Audit Trail

Добавлен единый локальный audit trail для Hub MCP и Codebase Memory proxy:

- общий writer `rag/mcp_audit.py` пишет daily append-only JSONL в ignored `storage/mcp-audit/`;
- event contract фиксирует timestamp, server, transport, safe project, tool/class, duration, status, error category и result size;
- аргументы, query, source paths и contents, snippets, diff, findings, credentials, headers, environment и полные exception messages не записываются;
- добавлены best-effort запись, process-safe append и retention daily files по умолчанию 30 дней;
- MCP tool `get_mcp_usage_summary` возвращает bounded aggregate calls/errors по tools и servers, пропуская поврежденные строки и собственный вызов;
- добавлены тесты sanitization, errors, failure isolation, project filtering, proxy-compatible events, retention и summary.

Обновлены architecture, runtime observability, MCP/security policy, command reference и matching docs-site pages.
