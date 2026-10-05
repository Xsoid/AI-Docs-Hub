# 2026-10-06: Canonical Hub Documentation

`docs/` стал единственным ручным источником для Hub architecture, operations и standards. `scripts/generate-hub-pages` создает их Starlight-представления с generated marker; output исключен из Git и не редактируется вручную.

Генератор запускается перед Astro `dev`/`build` и через Make target `hub-pages`, поэтому сайт получает тот же Markdown, который используется как canonical Hub documentation. Это устраняет 20 ручных пар docs↔docs-site и не допускает их повторного появления.

Проверка: generation, Astro build, link rendering и unit test generator contract.
