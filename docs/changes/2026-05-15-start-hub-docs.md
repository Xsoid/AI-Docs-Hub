# 2026-05-15: Запуск Документации Хаба В `/docs`

## Кратко

Создано дерево документации `/docs` для AI Docs Hub.

## Что Изменилось

- Добавлен индекс `/docs` и source-of-truth правило для документации хаба.
- Добавлен обзор архитектуры текущих локальных слоев хаба.
- Добавлен runbook локального runtime.
- Добавлены design notes по runtime observability для явных статусов `up/down/degraded`.
- Добавлен стандарт сопровождения документации.
- Добавлен ADR, принимающий `/docs` как documentation area хаба.

## Эксплуатационное Наблюдение

`make healthcheck` проверяет repository health и prerequisites, но не доказывает, что docs-site активно слушает `http://localhost:4321/`.

Пока нет отдельных observability commands, runtime-состояние docs-site нужно проверять так:

```sh
lsof -nP -iTCP:4321 -sTCP:LISTEN
curl -sS -I --max-time 3 http://localhost:4321/
```

## Проверка

Перед добавлением новой структуры `/docs` были прочитаны существующие architecture и standards docs.

## Follow-Up

- Реализовать `make hub-status`.
- Реализовать явный foreground `make hub-dev`.
- Решить, должен ли docs-site рендерить `/docs` напрямую или зеркалировать выбранные страницы.
