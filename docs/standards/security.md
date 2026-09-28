# Security Standard

AI Docs Hub читает локальные проектные файлы, поэтому security policy сфокусирована на secret hygiene и namespace isolation.

## Secret-Looking Paths

Не индексировать и не включать в generated context:

- `.env`, `.env.*`;
- private keys: `*.key`, `*.pem`, `*.p12`, `*.pfx`;
- paths с `secret`, `token`, `password`, `credential`, `cookie`, `session`, `dump`;
- `node_modules`, `.git`, cache, tmp и logs.

## Content Scan

Перед indexing и generated context выполняется scan на:

- private key blocks;
- AWS-like keys;
- GitHub tokens;
- OpenAI-like keys;
- generic `secret`, `token`, `password`, `api_key` assignments.

Если scan находит suspicious content, indexing/generated read для этого project должен быть blocked или skipped с warning.

Lite RAG indexing использует режим skip: suspicious source files не читаются в chunks, а список пропусков сохраняется в index security metadata и показывается в status diagnostics.

## Path Safety

Read operations должны использовать safe path resolution относительно project root. Запросы на path traversal или excluded path должны отклоняться.

Skill Intelligence применяет те же exclude, safe path и secret scanning правила. Secret-looking skill content блокирует validation/apply. Запись proposal по умолчанию является dry-run; при `confirm=true` разрешены только exact proposal targets внутри external project root: `.agents/skills/**`, `docs/**` и root `AGENTS.md`. Сам checkout AI Docs Hub запрещен как write target. Перед каждой записью проверяются containment, exclude rules, secret patterns и ожидаемый hash существующего target.

Внешние docs, skills, proposals и audit reports подключенных проектов нельзя сохранять в tracked AI Docs Hub files. Их project-derived copies допустимы только в ignored local storage.

## Namespace Isolation

- Не смешивать project namespaces без прямого запроса пользователя.
- MCP `--project` scope должен запрещать calls в другой project.
- Search output должен показывать project and namespace metadata.

## External Services

Default stack не отправляет project contents во внешние APIs и не использует cloud vector DB.

## Lifecycle Reports

Project Lifecycle stores only local ignored metadata and digests. Review records must not contain external project source snippets, full diff, generated AGENTS content, real absolute project paths or secrets. Secret scan and path safety remain hard invariants; missing optional security tooling is not passed silently.
