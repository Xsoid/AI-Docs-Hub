# AI Docs Hub

Локальный AI Docs Hub - это инфраструктурный хаб для проектной документации, `llms.txt`, локального RAG-индекса и MCP-доступа для Codex и других ИИ-агентов.

Главное правило: документация конкретного проекта хранится внутри этого проекта. Хаб читает подключенные проекты по YAML-конфигам, строит производные индексы и отдает контекст агентам.

## 1. Что это такое

Хаб объединяет несколько слоев:

- docs-as-code: строгая структура документации внутри каждого проекта;
- llms.txt: воспроизводимая генерация `llms.txt`, `llms-full.txt`, `llms-small.txt`;
- lite RAG: локальный индекс в `storage/index`;
- MCP bridge: stdio-сервер с инструментами для Codex;
- templates: шаблоны архитектуры, модулей, ADR, API, deployment, glossary и правил агентов;
- operation logs: JSONL-логирование всех операций индексирования;
- wiki-links: парсинг и валидация `[[ссылок]]` между документами;
- lint: структурная проверка качества документации (broken links, orphan pages, empty documents).

## 2. Почему система локальная

По умолчанию хаб:

- не отправляет содержимое проектов во внешние API;
- не использует облачные vector DB;
- не меняет реальные проекты;
- поддерживает явную настройку глобального `~/.codex/config.toml` для Codex/MCP;
- хранит индексы и generated-файлы локально в `storage/`.

## 3. Архитектура

```text
ai-docs-hub/
  configs/projects/       # подключение внешних проектов
  docs/                   # source-документация самого AI Docs Hub
  docs-site/              # Astro Starlight docs-site
  rag/                    # lite RAG backend
  mcp/                    # stdio MCP server
  scripts/                # команды в Makefile
  templates/project-docs/ # шаблоны проектной документации
  storage/                # локальные индексы и generated artifacts
```

Рабочая архитектура не требует Docker, RAGFlow, облачных vector DB или внешних AI API. По умолчанию хаб работает через локальный Python, локальный Node/npm для docs-site и файловое хранилище в `storage/`.

## 4. Где хранится документация проектов

Внутри каждого проекта:

```text
project-a/
  AGENTS.md
  README.md
  docs/
    architecture/
    modules/
    decisions/
    api/
    deployment/
    glossary.md
```

Внутри хаба хранятся только конфиги, индексы, MCP, docs-site, шаблоны, generated-представления, надпроектные правила и документация самого хаба в `/docs`.

## 4.1. Где документируются доработки хаба

Документация самого AI Docs Hub ведется в:

```text
docs/
```

Каждая значимая доработка хаба должна обновлять `/docs` в том же изменении. Начальная структура и правила описаны в [docs/README.md](docs/README.md).

## 5. Что должно быть установлено для автономной работы

Для автономного запуска без контейнеров на машине должны быть доступны:

- Python 3.11 как `python3.11`;
- Node.js 22 LTS как `node`;
- npm 10+ как `npm`;
- Git;
- `make`.

На macOS с Homebrew:

```sh
brew install python@3.11 node@22
brew link --force --overwrite node@22
```

Важно: системный `python3` на macOS может быть старым. Команды хаба намеренно используют `python3.11`.

Docker не является runtime-зависимостью хаба. Он не нужен для Lite RAG, MCP, `llms*.txt`, индексирования, lint, watch mode или docs-site, если локально установлен Node.js 22.

## 6. Быстрый старт

```sh
make setup
make healthcheck
make llms
make mcp-test
```

Интернет потребуется только для установки npm-зависимостей:

```sh
make setup
```

Эквивалентно для docs-site вручную:

```sh
./scripts/docs-npm install
```

Проверить live runtime-состояние хаба:

```sh
make hub-status
```

Запустить docs-site и watcher вместе в явном foreground-режиме:

```sh
make hub-dev
```

`hub-dev` не прячется в фоне: он пишет логи в текущий терминал и останавливает дочерние процессы при `Ctrl+C`.

Установить persistent runtime через macOS `launchd`:

```sh
make hub-install
make hub-start
make hub-status
```

Остановить persistent runtime:

```sh
make hub-stop
```

Посмотреть runtime-логи:

```sh
make hub-logs
```

Открыть простой GUI dashboard:

```text
http://localhost:4321/status/
```

Запустить иконку в верхнем баре macOS:

```sh
make hub-menu-start
```

Собрать `.app` без запуска:

```sh
make hub-menu-build
```

Собранное приложение лежит в `build/AI Docs Hub.app`, но `build/` не коммитится и остается локальным артефактом.

Закрыть иконку:

```sh
make hub-menu-stop
```

Пересобрать и перезапустить иконку после изменения Swift-кода или текста в верхнем баре:

```sh
make hub-menu-restart
```

## 7. Как добавить проект

Создайте файл:

```text
configs/projects/my-project.yaml
```

Пример:

```yaml
project: my-project
namespace: my-project
title: "My Project"
root: "${AI_DOCS_PROJECTS_ROOT}/my-project"
docs_backend: auto
mkdocs_config: "mkdocs.yml"

sources:
  - path: "docs"
    type: markdown
  - path: "README.md"
    type: markdown
  - path: "AGENTS.md"
    type: markdown

include:
  - "docs/**/*.md"
  - "README.md"
  - "AGENTS.md"
  - "src/**/README.md"
  - "migrations/**/*.sql"

exclude:
  - ".git/**"
  - "node_modules/**"
  - ".env"
  - ".env.*"
  - "**/.env"
  - "**/.env.*"
  - "**/*secret*"
  - "**/*token*"
  - "**/*password*"
  - "**/*.key"
  - "**/*.pem"

agent_rules:
  - "Искать только в namespace текущего проекта."
  - "Если документация противоречит коду, явно сообщать о конфликте."
```

`root` не должен быть hard-coded абсолютным путем в репозитории. Используйте переносимое выражение:

- `${AI_DOCS_PROJECTS_ROOT}/project-name` для проектов рядом с хабом; по умолчанию `AI_DOCS_PROJECTS_ROOT` разворачивается в родительскую директорию checkout хаба;
- относительный путь от корня хаба;
- host-specific абсолютный путь только во внешнем локальном конфиге, который не коммитится.

`docs_backend` управляет тем, как хаб обнаруживает документацию проекта:

- `auto` - значение по умолчанию; если рядом с проектом есть `mkdocs.yml` или `mkdocs.yaml`, хаб использует его `docs_dir`, `exclude_docs` и `draft_docs`, иначе работает по обычным `include`;
- `mkdocs` - ожидать MkDocs-конфиг, но не падать при его отсутствии; хаб покажет warning и продолжит по `include`;
- `standard` - игнорировать MkDocs и использовать только `sources`/`include`/`exclude`.

Хаб не выполняет MkDocs `plugins` или `hooks`; конфиг используется только как read-only описание структуры документации.

Проверьте конфиг:

```sh
make validate-configs
```

Посмотреть, какие рекомендованные файлы документации Хаб может создать:

```sh
make scaffold-docs PROJECT=my-project
```

Создать недостающие файлы в подключенном проекте:

```sh
make scaffold-docs-write PROJECT=my-project
```

Запись в проект выполняется только этой явной командой. Dry-run не меняет файлы проекта. Scaffold покрывает не только базовые разделы, но и техническую документацию: configuration, security, data, integrations, observability, testing, troubleshooting, development, operations и infrastructure.

## 8. Как собрать docs-site

Docs-site - это веб-интерфейс для просмотра документации хаба и derived-страниц подключенных проектов. Он не нужен для MCP-доступа Codex, но удобен для ручной навигации по документации.

Обновить derived-страницы подключенных проектов:

```sh
make project-pages
```

Запустить dev server:

```sh
make docs-dev
```

Открыть в браузере:

```text
http://localhost:4321/
```

Собрать статический сайт:

```sh
make docs-build
```

Docs-site запускается локальным Node/npm. Перед `docs-dev`, `docs-build` и `llms` хаб обновляет derived-страницы проектов из `configs/projects/*.yaml`. Подключённые проекты не должны запускать hub: они остаются источниками документации, а hub читает их через `configs/projects`.

Docs-site построен на Astro Starlight. Starlight дает нормальные landmarks и доступную навигацию; если будущая тема ухудшит семантический HTML, overrides нужно добавлять в `docs-site`.

## 9. Как сгенерировать llms.txt

```sh
make llms
```

Файлы пишутся в:

```text
docs-site/public/llms.txt
docs-site/public/llms-full.txt
docs-site/public/llms-small.txt
storage/generated/llms.txt
storage/generated/llms-full.txt
storage/generated/llms-small.txt
```

Это производные артефакты. Не редактируйте их вручную.

## 10. Как проиндексировать проект

```sh
make index PROJECT=my-project
```

Полная переиндексация одного проекта:

```sh
make reindex PROJECT=my-project
```

Все проекты:

```sh
make index-all
```

Перед индексированием автоматически выполняется проверка на секреты. Если найден подозрительный файл или содержимое, индексация блокируется.

Автоматическая переиндексация при изменении документации:

```sh
make watch PROJECT=my-project
```

Следить за всеми валидными проектами:

```sh
make watch-all
```

Watcher работает локально в foreground-режиме, читает только файлы из `include`, применяет `exclude`, дебаунсит изменения, запускает secret scan перед обновлением индекса и после успешной индексации обновляет `llms*.txt`. Остановить его можно через `Ctrl+C`.

Для macOS launchd есть шаблон:

```text
templates/launchd/local.ai-docs-hub.watch.example.plist
```

Он не устанавливается автоматически. Скопируйте шаблон, замените `__AI_DOCS_HUB_ROOT__`, `__PYTHON3_11__` и `example-project` на значения конкретной машины, затем установите:

```sh
cp templates/launchd/local.ai-docs-hub.watch.example.plist ~/Library/LaunchAgents/local.ai-docs-hub.watch.my-project.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/local.ai-docs-hub.watch.my-project.plist
launchctl enable gui/$(id -u)/local.ai-docs-hub.watch.my-project
```

Отключение:

```sh
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/local.ai-docs-hub.watch.my-project.plist
rm ~/Library/LaunchAgents/local.ai-docs-hub.watch.my-project.plist
```

## 11. Как подключить MCP к Codex

Глобальный Codex config можно настраивать для подключения MCP. Пример лежит в:

```text
codex-config.example.toml
```

Содержимое:

```toml
[mcp_servers.local_ai_docs_hub]
command = "python3.11"
args = ["<AI_DOCS_HUB_ROOT>/mcp/server.py"]
```

Пример project-scoped config:

```text
project-codex-config.example.toml
templates/codex/project-config.toml
```

```toml
[mcp_servers.project_docs]
command = "python3.11"
args = ["<AI_DOCS_HUB_ROOT>/mcp/server.py", "--project", "example-project"]
```

## 12. Как проверить, что все работает

```sh
make healthcheck
make mcp-test
make llms
```

MCP tools:

- `list_projects`
- `get_project_profile`
- `search_docs`
- `read_doc`
- `search_decisions`
- `search_modules`
- `index_project`
- `healthcheck`
- `lint_project` — проверка структурного качества (broken links, orphan pages, empty documents)
- `read_operation_log` — чтение лога операций индексирования

`index_project` через MCP по умолчанию не запускает индексацию. Он сначала возвращает описание операции и требует `confirm=true`.

## 13. Как не утечь секретами

По умолчанию исключаются:

- `.env`, `.env.*`;
- private keys: `*.key`, `*.pem`, `*.p12`, `*.pfx`;
- пути с `secret`, `token`, `password`, `credential`, `cookie`, `session`, `dump`;
- `node_modules`, `.git`, `storage`, `cache`, `tmp`, `logs`.

Дополнительно контент сканируется на private key blocks, AWS keys, GitHub tokens, OpenAI-like keys и generic `secret/token/password/api_key` assignments.

Ручная проверка:

```sh
make check-secrets PROJECT=my-project
```

## 14. Как удалить индекс проекта

Индекс проекта - это локальный JSON-файл:

```text
storage/index/my-project.json
```

Удаление индекса не трогает проект:

```sh
rm storage/index/my-project.json
```

Удалить generated/cache:

```sh
make clean-cache
```

## 15. Operation Logs и Lint

### Логирование операций индексирования

Каждый проект автоматически ведет лог всех операций индексирования. Логи хранятся в JSONL-формате:

```text
storage/index/{project}_log.jsonl
```

Просмотр логов:

```sh
make logs PROJECT=my-project
```

Пример вывода:

```
📋 Operation Log: my-project
Timestamp                  Operation                 Details
--------------------------------------------------------------------------------
2026-05-12T19:51:03        index_complete            docs=13, chunks=176, 0.05s
2026-05-12T19:51:03        index_started             
```

Через MCP:

```python
mcp.read_operation_log({"project": "my-project", "limit": 20})
```

Отслеживаемые операции:
- `index_started` — индексирование началось
- `index_complete` — индексирование успешно завершено
- `index_error` — ошибка индексирования
- `secret_scan_blocked` — индексирование заблокировано из-за найденных секретов
- `lint_check` — проверка качества документации

### Проверка структурного качества документации (Lint)

Встроенный lint проверяет:

- **Broken wiki-links** — `[[ссылки]]` на несуществующие страницы
- **Orphan pages** — страницы, на которые никто не ссылается и которые ни на кого не ссылаются
- **Empty documents** — файлы без содержимого
- **Duplicate headings** — одинаковые заголовки в одном файле
- **Missing frontmatter** — отсутствующие метаданные (экспериментально)

Запуск lint для проекта:

```sh
make lint PROJECT=my-project
```

Пример вывода:

```
📋 Lint Report: my-project
Status: has_issues

📊 Statistics:
  • Documents: 14
  • Chunks: 83
  • Issues: 8

🔴 Issues breakdown:
  • orphan_pages: 8

📝 Issues:
  ℹ️ [orphan_page] docs/architecture.md: Page is not referenced by other pages and has no outgoing links
  ℹ️ [orphan_page] docs/database.md: Page is not referenced by other pages and has no outgoing links
  ...

💡 Recommendations:
  • Consider linking 8 orphan page(s) from other documents or removing them
```

Детальный lint с дополнительной информацией:

```sh
python3.11 scripts/lint-project --project my-project --detailed
```

JSON-вывод (для парсинга):

```sh
python3.11 scripts/lint-project --project my-project --json
```

Через MCP:

```python
mcp.lint_project({"project": "my-project", "detailed": false})
```

## 16. Как перенести хаб на другую машину

1. Скопируйте репозиторий хаба.
2. Установите локальные зависимости: Python 3.11, Node.js 22 LTS, npm, Git и `make`.
3. Не переносите `storage/index`, если хотите чистую переиндексацию.
4. Проверьте переносимые `root` в `configs/projects/*.yaml` и при необходимости задайте `AI_DOCS_PROJECTS_ROOT`.
5. Запустите:

```sh
make setup
make validate-configs
make llms
make index-all
make mcp-test
```

## 17. Безопасные ограничения MVP

- Хаб читает внешние проекты, но не редактирует их.
- Источник истины - project docs, а не RAG.
- Каждый проект индексируется в своем namespace.
- Глобальный Codex config редактируется только точечными настройками Codex/MCP.
- Никакие облачные vector DB не используются.
