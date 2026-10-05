# 2026-10-05: Project Connection Repair

Dashboard теперь честно различает полный Docs RAG и `security_skipped`: неполный индекс не рисуется подключенным, поэтому connection count совпадает с карточками.

Для неполной project connection matrix добавлена кнопка `Привести в порядок` (`project.repair`). Она не повторяет бесполезную генерацию context: exact blocked source paths, уже выявленные secret scan, добавляются только в локальный Hub binding `exclude`, после чего project page, RAG index и `llms*.txt` пересобираются. Подключенный проект и содержимое заблокированных файлов не изменяются и не выводятся.

Generated context передает число заблокированных источников и не предлагает `Собрать context`, пока причина не устранена этим безопасным workflow.

Проверка: unit tests dashboard/config editor, Hub status после repair, generated context и RAG status.
