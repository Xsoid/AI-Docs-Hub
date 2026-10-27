# Гонка В `make hub-restart`

## Что Изменилось

`scripts/hub-launchd` после `launchctl bootout` ждет, пока service исчезнет из домена `gui/<uid>`. Ожидание длится до 10 секунд с опросом каждые 0,2 секунды. Если service не выгружен, `stop`, `restart` и `uninstall` завершаются ошибкой `still loaded` и не запускают `bootstrap`.

## Почему

`launchctl bootout` возвращается раньше, чем launchd выгружает service. `make hub-restart` сразу проверял загрузку, видел еще загруженный service и пропускал `bootstrap`. Затем `kickstart` падал на уже выгруженном service, и runtime оставался остановленным.

## Эксплуатация

Если `make hub-restart` сообщает `still loaded`, повторите команду или выполните `make hub-launchd-status`. Поведение описано в `docs/operations/runtime-observability.md`, раздел `make hub-stop`.

## Проверка

```sh
make test
make hub-restart
```

`tests/test_hub_launchd.py` моделирует асинхронный `bootout` и таймаут выгрузки. До исправления первый тест падал на `kickstart`, как и реальный перезапуск.

## Follow-Up

Нет.
