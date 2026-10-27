# RAG Policy

Lite RAG в AI Docs Hub является локальным derived index поверх docs-as-code.

## Правила

- Каждый проект индексируется в собственном namespace.
- Search project-scoped по умолчанию.
- Индексация начинается с project config validation, source discovery, exclude filtering и secret scan.
- Secret-looking source files пропускаются и записываются в index security metadata; их содержимое не попадает в chunks/search results.
- `.env`, private keys, tokens, cookies, sessions, credentials, dumps и secret-looking files не индексируются.
- RAG output должен возвращать source path, section/heading, score, confidence, updated timestamp, content hash и snippet.
- Каждый результат объясняет совпадение:
  - `matched_terms` - различные нормализованные термины запроса, найденные в heading или тексте chunk, в порядке запроса;
  - `heading_match` - найден ли хотя бы один из них в heading; такое совпадение повышает score в 1,5 раза;
  - `query_coverage` - доля различных терминов запроса из `matched_terms`, округленная до трех знаков.
- Объяснение содержит только термины запроса и не добавляет фрагменты текста. Низкий `query_coverage` - сигнал переформулировать запрос, например другим языком или термином.
- RAG index не является source of truth.

## Ранжирование

`search_index` в `rag/lite.py` ранжирует chunks при каждом поиске. Переиндексация после изменения правил не нужна.

- Score - BM25 с `k1 = 1.2` и `b = 0.75` по токенам heading и текста chunk. Средняя длина считается по chunks namespace после `path_filter`.
- Совпадение термина в heading умножает его вклад на 1,5.
- Score умножается на вес типа источника (`source_weight`, поле `source_weight` в результате). Правила проверяются по порядку, первое совпадение решает:
  - `0.6` - каталоги `tests/` и `test/`, файлы `*Tests.*`, `*test.*`, `test-*`, `test_*`, `*_test.*`, `CHANGELOG*`, каталог `docs/changes/`;
  - `1.25` - каталоги `decisions/`, `adr/`, `architecture/`, файлы `adr-*`, `AGENTS.md`, `CLAUDE.md`, `README.md`;
  - `1.0` - остальные.
- Каждый файл представлен в выдаче одним лучшим chunk.
- При равном score порядок определяет `source_path`.
- `confidence = min(0.99, score / (score + 6))` - монотонное сжатие score. Это не калиброванная вероятность. Шкала изменилась при переходе на BM25 2026-10-28.
- Optional `min_confidence` (0–1, по умолчанию 0) отбрасывает результаты с меньшим `confidence`. По умолчанию результаты не отсекаются.

Изменение весов или правил принимается только с набором оценки `tests/fixtures/search-eval/` и `tests/test_search_quality.py`: метрики не должны быть хуже зафиксированных. Пересчитать метрики можно командой `python3.11 -m tests.search_eval`. Набор содержит только synthetic-данные. Запрос на английском по документации на русском ранжированием не решается и остается в наборе как известный промах.

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

Watcher poll-ит configured include paths, MkDocs config path при enabled source discovery, применяет exclude rules, debounces changes, запускает secret scan, обновляет local project index, после успешного indexing регенерирует `llms*.txt` и обновляет read-only Skill Intelligence audit. Автоматический audit можно отключить только явным `--no-skill-audit`.

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
