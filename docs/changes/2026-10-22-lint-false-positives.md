# Lint False Positives

## Что Изменилось

- `lint_project` проверяет broken wiki-links и orphan pages только в Markdown. Bash-условия `[[ -n "$x" ]]` в `.sh` больше не считаются wiki-links, а code files не попадают в orphan pages.
- Orphan check учитывает относительные Markdown-ссылки на `.md` files наряду с wiki-links.
- Skill reference check пропускает inline code с пробелами (команды вроде `python3 scripts/search.py`) и path templates с `{}` или `<>`.
- Путь в inline code скилла может быть относительным к project root, потому что агенты работают из корня проекта. Markdown-ссылка по-прежнему резолвится от файла скилла.
- Ownership conflict check не учитывает слова из ссылок и путей в скилле. Ссылка на canonical doc — рекомендованное исправление, а не дублирование.
- `verify_patch` name heuristic пропускает design-token files только после clean content scan самого файла. `oauth-token.json`, `tokens.json` и похожие paths по-прежнему блокируются.
- Quality profile находит вложенный `*/Cargo.toml` и `scripts/test-*.sh` как required verification checks. Раньше для QADREN список checks был пустым, и `verify_patch` не запускал тесты.
- Secret content scan не считает identifier без цифр перед `)` (`api_key=api_key)`, `session: URLSession)`) assigned secret и не считает unquoted call expression (`password: z.string().min(8)`) assigned secret. Literal assignments по-прежнему блокируются.

## Почему

Панель Хаба показывала для QADREN 9 broken links, 76 orphan pages и `blocked` Skill Intelligence. Почти все записи были ложными срабатываниями: link checks шли по shell и Rust/Swift коду, документация QADREN использует Markdown-ссылки, а vendored skill с примером формы на zod блокировался secret scan.

## Эксплуатация

После обновления повторите `make lint PROJECT=name` и skill audit, чтобы обновить сохраненный статус панели. Оставшиеся skill warnings — реальные ссылки на отсутствующие файлы или heuristic-предупреждения.

## Проверка

```sh
python3.11 -m unittest discover -s tests
make docs-check
```

## Follow-Up

`_skill_diagnostics` сообщает `secret_content` для любого нечитаемого skill, включая missing file и превышение размера.
