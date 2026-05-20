# llms.txt Policy

`llms.txt`, `llms-full.txt` и `llms-small.txt` являются generated artifacts.

## Генерация

```sh
make llms
```

Команда читает:

- hand-authored docs-site pages из `docs-site/src/content/docs`;
- configured project docs из валидных `configs/projects/*.yaml`;
- только files, разрешенные project source plan;
- только content, который прошел secret scan.

## Outputs

```text
docs-site/public/llms.txt
docs-site/public/llms-full.txt
docs-site/public/llms-small.txt
storage/generated/llms.txt
storage/generated/llms-full.txt
storage/generated/llms-small.txt
storage/generated/llms-report.json
```

`storage/generated/llms-report.json` фиксирует docs count, warning-и и output paths.

## Правила

- Не редактировать generated `llms*.txt` вручную.
- При изменении source docs или docs-site content можно регенерировать через `make llms`.
- Если project config invalid или root недоступен, project может быть skipped и попадет в report warnings.
- RAG indexes и `llms*.txt` не являются source of truth.
