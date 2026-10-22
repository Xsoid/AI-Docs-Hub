# Claude Code Client Support

## Что Изменилось

Hub поддерживает Claude Code как второй агентский клиент рядом с Codex.

- `scripts/claude-mcp` регистрирует Hub MCP servers в local scope `~/.claude.json`: `<project>_docs`, `codebase_<project>` при наличии binary и graph и `local_ai_docs_hub` для checkout Hub.
- `scripts/project-lifecycle record-review` записывает code или security review без MCP с той же проверкой fingerprint.
- Skills `code-review` и `security-review` описывают review для Codex и Claude Code.
- Managed lifecycle и Codebase Memory routing blocks больше не называют Codex единственным клиентом. Существующие blocks подключенных проектов обновятся при следующем onboarding.

## Почему

Claude Code не читает `~/.codex/config.toml`. Без регистрации у него нет Hub MCP tools, и он не может записать review для gate.

## Эксплуатация

Регистрация по умолчанию работает как dry-run. Запись меняет только Hub-managed entries выбранного project dir. После записи перезапустите Claude Code. Процедура: `docs/operations/claude-code.md`.

## Проверка

```sh
python3.11 -m unittest discover -s tests
make docs-check
```

## Follow-Up

Dashboard `/status/` пока не показывает Claude Code registration. `fully_connected` в Codebase Memory status отражает только Codex.
