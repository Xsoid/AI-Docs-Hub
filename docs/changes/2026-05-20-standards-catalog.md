# 2026-05-20 - Standards Catalog

## Что Изменилось

Documentation standard получил явный каталог стандартов хаба:

- documentation;
- RAG;
- MCP;
- `llms.txt`;
- runtime/status;
- project config;
- source discovery;
- generated artifacts;
- scaffold;
- security.

Также добавлены явные sections для project config, runtime/status, generated artifacts и path portability.

## Поведение

Если новое поведение хаба не укладывается в существующие standard groups, нужно добавить или расширить standard section до того, как считать поведение установленным.

## Проверка

Выполнены:

- `./scripts/docs-npm run build`;
- `git diff --check`.
