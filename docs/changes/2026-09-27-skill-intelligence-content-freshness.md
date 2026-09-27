# 2026-09-27 - Content-based freshness для Skill Intelligence

## Что изменилось

Skill Intelligence сохраняет SHA-256 содержимого каждого разрешенного source-файла в audit snapshot и использует его для проверки freshness. Простое изменение `mtime` без изменения текста больше не переводит проект в `STALE`. Reports, созданные до добавления hash, временно проверяются по прежним `mtime_ns`/`mtime`-полям до следующего audit.

## Проверка

- Unit test проверяет, что touch неизменного source-файла оставляет audit fresh, а изменение содержимого переводит его в stale.
- `make skill-audit PROJECT=mammonite` подтверждает `audited/fresh`, `changed_paths: []` после явного обновления отчёта.
