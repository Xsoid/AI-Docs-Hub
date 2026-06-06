# RAG Policy

Lite RAG в AI Docs Hub является локальным derived index поверх docs-as-code.

## Правила

- Каждый проект индексируется в собственном namespace.
- Search project-scoped по умолчанию.
- Индексация начинается с project config validation, source discovery, exclude filtering и secret scan.
- Secret-looking source files пропускаются и записываются в index security metadata; их содержимое не попадает в chunks/search results.
- `.env`, private keys, tokens, cookies, sessions, credentials, dumps и secret-looking files не индексируются.
- RAG output должен возвращать source path, section/heading, score, confidence, updated timestamp, content hash и snippet.
- RAG index не является source of truth.

## Storage

Indexes хранятся в:

```text
storage/index/{project}.json
```

Operation logs хранятся в:

```text
storage/index/{project}_log.jsonl
```

Эти файлы являются runtime/generated artifacts и не редактируются вручную как документация.

## Watch Mode

```sh
make watch PROJECT=project-name
make watch-all
```

Watcher poll-ит configured include paths, MkDocs config path при enabled source discovery, применяет exclude rules, debounces changes, запускает secret scan, обновляет local project index и после успешного indexing регенерирует `llms*.txt`.

## Status Diagnostics

`/status/` и `make hub-status` показывают:

- backend;
- index presence;
- source file count;
- indexed document count;
- chunk count;
- index path;
- indexed timestamp;
- newest source timestamp;
- freshness per project;
- next step для missing или stale indexes.

Stale index является operational warning, потому что search results могут отставать от docs-as-code.

## Repair Action

Dashboard и scripts могут исправлять `missing`, `stale` или unreadable project index через allowlisted action:

```text
rag.reindex
```

Action принимает только существующий project config, сохраняет project namespace isolation, запускает обычную индексацию:

```sh
python3.11 scripts/index-project --project <project> --reindex
```

После успешной индексации action регенерирует `llms*.txt`. Secret scan, exclude rules и path safety остаются теми же, что и при ручном `make reindex PROJECT=<project>`.

Если secret scan находит suspicious файлы, `rag.reindex` индексирует только безопасные файлы проекта и оставляет предупреждение `security_skipped` в status diagnostics. Полное индексирование возможно только после исправления project docs или exclude rules в project config.
