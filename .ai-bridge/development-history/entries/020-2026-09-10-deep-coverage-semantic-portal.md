# 020 — Deep specification coverage и semantic-first portal

**Период:** 2026-09-10
**Источник:** `Восстановление контекста Sphinx Needs -- 6aa2a4db-4ca4-83ed-9942-b0cec6c362f8.md`

## Specification coverage реализован

- Новый слой строили поверх **authoritative Sphinx-Needs graph**, без второго graph engine.
- Через native `network_back` добавлены отсутствовавшие structural laws:
  - GOAL должен иметь FEATURE;
  - FEATURE должен иметь REQ.
- Найден старый false-green defect: Sphinx-Needs правильно фейлил stale revision-link, но Verification Matrix могла всё равно показать старый passed evidence как текущий.
- Исправление сделано через structured `NeedLink.condition` из публичного Sphinx-Needs API, без повторного парсинга JUnit/Markdown и без собственного condition parser.
- Введены различия **current / outdated / predated** evidence.
- Lifecycle уточнён: `required_evidence` является release obligation только для `accepted`; draft/deprecated сохраняют contract, но не должны закрывать текущий release.
- Добавлен recursive **deep health** поверх существующего graph/evidence.
- На исходном `llm-router`: 9/9 Goals, 15/15 Features, 29/29 REQ и 12/12 TREQ были deep-covered без подгонки требований.

## Requirements hygiene

Ручной semantic audit нашёл три реальных layering-дефекта:

- cache invalidation вынесен из product REQ в `TREQ_CONFIG_CACHE_INVALIDATION`;
- retry classification — в `TREQ_PROVIDER_RETRY_CLASSIFICATION`;
- repair prompt bounds — в `TREQ_REPAIR_PROMPT_BOUNDS`.

Parent REQ подняты до revision 2, существующее актуальное evidence repinned; новые TREQ начали с revision 1.

Итог после нормализации: **29/29 REQ + 15/15 TREQ deep-covered, 0 gaps**.

Сознательно не добавлены:

- второй StrictDoc-style coverage tree — hierarchy уже даёт native `needflow`;
- Doorstop fingerprints / semantic-diff engine;
- собственный impact engine — impact остаётся обязанностью **ubCode**.

## Главная UX-коррекция

Пользователь отверг портал как «набор таблиц»: техническая корректность не давала понятного пути от исходного замысла до доказательств.

Новая информационная архитектура строится вокруг **смысла, а не типа артефакта**.

Главная даёт три маршрута:

1. **Audit an idea end to end** — Goal → Feature → REQ → optional TREQ → implementation/test → evidence.
2. **Follow a relationship or change** — окружение идеи, связи и impact.
3. **Check release confidence** — что мешает считать контракт доказанным.

Requirements Hub заменён на **Intent Map**: Goals сгруппированы по продуктовым смыслам, а полные каталоги REQ/Feature/TREQ оставлены только как reference.

В каждой product-area page одинаковый zoom-flow и локальная semantic hierarchy через native Sphinx-Needs `needflow/needlist`. Глобальные Verification / Tests / Traceability стали advanced diagnostics, а не обязательным маршрутом чтения.

## Важные owner-level дефекты, найденные новым flow

- Обычный reusable CI строил только `build html --junit`, поэтому Living Specifications отсутствовали: Allure evidence не передавался.
- Исправлено в **infra-ci**, а не consumer workaround:
  обычный CI теперь делает `build portal --junit … --allure-results …`, без live examples.
- Для stable semantic navigation добавлены area anchors.

## Live publication выявила ещё реальные дефекты

- Provider/model routes в Sphinx-Gallery были quota/permission-sensitive; их перераспределили по уже существующим стабильным routes после реальных live probes, без retry/sleep hacks.
- Randomized pre-push поймал flaky rate-limit BDD: окно блокировки 50 ms зависело от scheduling. Test setup исправлен на детерминированное ~5 s окно без изменения runtime.
- Release automation отдельно исправлена так, чтобы version обновлялся одновременно в `pyproject.toml` и `uv.lock`.
- Dossier обнаружил ещё один ownership mismatch: PDF build получал JUnit, но не Allure, поэтому Living Specs refs отсутствовали. DocOps dossier получил optional `--allure-results` и использует **тот же renderer/path**, что portal; infra-ci передаёт оба evidence sources.

## Требования пользователя

- Портал должен давать 2–3 интуитивных маршрута, а не заставлять изучать каталоги объектов.
- Нужно видеть **весь путь от идеи до доказательства**, легко нырять глубже и возвращаться к соседним смыслам.
- Не добавлять отдельный graph/UI, если Sphinx-Needs уже умеет hierarchy/links.
- Green status нельзя получать ценой подгонки requirements.
- Любой новый CI/docs defect исправлять в правильном owner-layer.
- Другие consumers не трогать.

## Точка остановки

Owner fixes уже были доведены до pilot, но финальная publication/release цепочка в этом источнике ещё не была завершена.
