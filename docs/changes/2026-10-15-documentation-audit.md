# Документационный Аудит И Канонические Generated Pages

Дата: 2026-10-15

AI Docs Hub теперь генерирует Hub architecture, operations и standards pages только из `docs/`. Генератор проверяет collisions, не перезаписывает site-only pages и удаляет только устаревшие marked output внутри managed directories.

Добавлены canonical style guide, documentation audit, `make docs-audit` и `make docs-check`. Проверки не используют внешние API и не заявляют полное соответствие ASD-STE100.

Подробная матрица устраненных повторов: [аудит документации](../operations/documentation-audit.md). ADR 0002 фиксирует замену открытого follow-up из ADR 0001.
