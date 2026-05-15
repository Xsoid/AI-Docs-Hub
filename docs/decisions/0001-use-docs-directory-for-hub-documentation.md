# 0001: Использовать `/docs` Для Документации Хаба

Дата: 2026-05-15

Статус: Accepted

## Контекст

В репозитории уже есть docs-site content в `docs-site/src/content/docs`, generated context files, RAG-индексы, templates и эксплуатационные scripts.

Но не было заполненной директории `/docs` для source-документации самого хаба. Из-за этого эксплуатационные решения, runtime behavior и follow-up улучшения было сложно отслеживать в одном стабильном месте.

Пользователь явно потребовал, чтобы все доработки AI Docs Hub документировались в `/docs`.

## Решение

`/docs` является source-документацией самого AI Docs Hub.

Документация подключенных проектов остается внутри этих проектов. RAG-индексы, generated project pages и `llms*.txt` остаются derived-артефактами.

`docs-site/` может продолжать предоставлять web documentation experience, но новая hub-level эксплуатационная и проектная документация должна сначала писаться в `/docs`, если будущий decision не введет автоматическую синхронизацию или миграцию.

## Последствия

Плюсы:

- у design и operations хаба появляется одно очевидное место source-документации;
- runtime-пробелы и решения можно отслеживать без смешивания с generated-артефактами;
- у будущих изменений появляется явное documentation obligation.

Tradeoff-ы:

- часть существующей документации все еще живет в `docs-site/src/content/docs`;
- maintainers должны избегать расходящихся duplicate pages;
- может понадобиться будущая интеграция docs-site, если `/docs` должен просматриваться через Astro.

## Follow-Up

- Решить, должен ли docs-site читать или зеркалировать `/docs`.
- Добавить runtime observability commands, описанные в `docs/operations/runtime-observability.md`.
- Вести будущие change notes в `docs/changes/`.
