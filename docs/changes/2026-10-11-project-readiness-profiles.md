# Project-specific Documentation Readiness Profiles

Date: 2026-10-11

AI Docs Hub теперь позволяет local project binding объявить собственный checklist канонических documentation paths через `documentation_readiness.items`.

Это устраняет ложные recommendations для проектов, где документация уже организована не по универсальному scaffold. Profile проверяет только project-relative files/directories и Markdown-содержимое каталогов; он не меняет RAG include/exclude, не создаёт файлы и не изменяет документацию подключенного проекта.

Проверка: schema validation и unit tests покрывают существующие canonical paths, точечное missing diagnostic и запрет traversal/unknown fields.
