# Ротация Runtime-Логов

## Что Изменилось

- Новый модуль `rag/runtime_logs.py` владеет путями `storage/logs/`, лимитами и функцией `rotate_stream`. `scripts/hub-launchd`, `scripts/hub-status`, `scripts/hub-dev` и `scripts/apply-fix` берут пути из него.
- `scripts/hub-dev` ротирует `hub-runtime.out.log` и `hub-runtime.err.log` по размеру: 10 МБ на файл, 3 архива.
- `scripts/apply-fix` хранит последние 50 файлов `apply-fix-*.log`.
- `make hub-logs` с `-f` использует `tail -F` и продолжает показ после ротации.

## Почему

launchd только дописывает `StandardOutPath`. `hub-runtime.out.log` вырос до ~45 МБ без ограничения.

`newsyslog` требует системной конфигурации в `/etc` и прав администратора. Ротация при старте не ограничивает долго работающий процесс. Поэтому ротацию выполняет сам supervisor, который единственный пишет в эти файлы.

## Эксплуатация

- Выполните `make hub-restart`, чтобы запущенный runtime получил новый код. Переустанавливать plist не нужно: он не изменился.
- Первая итерация после перезапуска переносит накопленный лог в `hub-runtime.out.log.1`.
- Политика описана в `docs/operations/runtime-observability.md`, раздел «Ротация Логов».

## Проверка

```sh
make test
```

`tests/test_runtime_logs.py` проверяет ротацию, лимит архивов, отказ ротировать чужой поток и очистку `apply-fix` logs. Сценарий launchd проверен вручную: stdout дописывается в файл больше лимита, после ротации старое содержимое лежит в `.1`, новые строки пишутся в новый файл.

## Follow-Up

Нет.
