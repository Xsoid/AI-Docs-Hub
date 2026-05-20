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

## Path Safety

Read operations должны использовать safe path resolution относительно project root. Запросы на path traversal или excluded path должны отклоняться.

## Namespace Isolation

- Не смешивать project namespaces без прямого запроса пользователя.
- MCP `--project` scope должен запрещать calls в другой project.
- Search output должен показывать project and namespace metadata.

## External Services

Default stack не отправляет project contents во внешние APIs и не использует cloud vector DB.
