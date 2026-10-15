# Стиль Технического Письма

## Назначение И Границы

Этот документ задает стиль для текущих инструкций AI Docs Hub. Он не изменяет технические контракты. Не меняйте кодовые блоки, команды, API fields, YAML/JSON, имена сущностей, security constraints или исторические документы ради сокращения текста.

Русский профиль — внутренний Controlled Technical Russian. Он адаптирует полезные принципы ASD-STE100, но не является соответствием ASD-STE100 или ГОСТ. Английский профиль — ASD-STE100-aware writing. Он учитывает официальный [ASD-STE100 Issue 9](https://www.asd-ste100.org/STE_downloads.html), но Hub не проверяет официальный словарь или все языковые правила и не заявляет полного соответствия.

## Нормативные Слова

| Значение | Русский | English |
| --- | --- | --- |
| Обязательное требование | должен; запрещено | MUST; MUST NOT |
| Рекомендация | рекомендуется | SHOULD; SHOULD NOT |
| Разрешение или возможность | может | MAY |

Используйте эти слова только для требований. Укажите субъект, условие и результат.

## Controlled Technical Russian

- Используйте один термин для одной сущности. Используйте термины из глоссария ниже.
- Пишите короткие предложения. В шаге процедуры описывайте одно действие.
- Ставьте условие перед действием. Называйте вход, ожидаемый результат, ошибку и восстановление, если они важны.
- Предпочитайте явный субъект и активный залог, когда это делает действие точнее.
- Используйте однозначные отрицания. Не удаляйте необходимое `не` при редактировании.
- Ссылайтесь на канонический документ вместо пересказа его правила.

Плохо: «При необходимости можно в целом обновить соответствующую документацию сайта.»

Хорошо: «После изменения документа в `docs/` выполните `make hub-pages`. Не редактируйте страницу с generated marker.»

## ASD-STE100-Aware English

- Use a short sentence with an explicit actor and action.
- Put the condition before the action.
- Use one instruction per step and consistent terms.
- Preserve approved technical nouns, verbs, API names, paths, and code identifiers.
- Review English prose against the official Issue 9 when formal STE conformance is required.

The local audit cannot validate the official STE dictionary, grammar exceptions, or semantic ambiguity. A human review remains required.

## Hub Glossary

| Term | Meaning |
| --- | --- |
| Hub | This AI Docs Hub repository and its local runtime. |
| connected project | An external project referenced by a local config. |
| canonical document | The one editable source that owns a rule or contract. |
| site-only page | A tracked docs-site entry page that contains navigation, not a duplicate rule. |
| generated page | A page with the Hub generator marker. |
| derived artifact | Local output that can be regenerated from a canonical input. |

## Local Audit

`make docs-audit` reports blocking ownership and internal-link errors. It also reports advisory long-sentence candidates. `make docs-check` returns nonzero only for blocking errors. The audit does not alter text, delete duplicate candidates, call external APIs, or certify ASD-STE100 compliance.
