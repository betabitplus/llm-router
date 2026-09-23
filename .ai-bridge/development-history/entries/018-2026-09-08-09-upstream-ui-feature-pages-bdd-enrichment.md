# 018 — Удаление custom UI, Feature pages и enrichment BDD evidence

**Период:** 2026-09-08 → 2026-09-09
**Источник:** `Восстановление контекста Sphinx Needs -- 6aa077bc-88e4-83ed-b3f7-cef61ca7308c.md`

## Главное

- Продолжили исправлять ошибку предыдущего этапа: собственный UI-layer признан лишним.
- Жёсткая граница стала такой:
  - **Ternforge/DocOps вычисляет semantics и собирает данные**;
  - **PyData Sphinx Theme / Sphinx Design / Sphinx-Needs / MyST / Pygments / Allure / Rich** отвечают за presentation.
- Living Specifications переведены на штатные Sphinx Design dropdowns/headings/cards вместо самодельных spacing/shadow/layout hacks.
- Реальная browser-проверка обнаружила ошибку Allure deep-link: правильный Allure 3 route — **`#<result-id>`**, без `#testresult/`.
- Важное правило закрепилось повторно: DOM/наличие ID недостаточно — интерактивные ссылки надо проверять реальным браузером.

## Аудит UI всей системы

Выяснилось, что та же ошибка оставалась в Engineering Experiments:

- большой custom JS/CSS слой переставлял DOM, рисовал tabs/panels/grid;
- это фактически был второй mini frontend framework.

EXP переведены на stock Sphinx Design/MyST/IPython primitives.

Дополнительно исправлена граница causal digest:

- presentation-only helpers больше не должны делать empirical evidence stale;
- изменение способа показа результата ≠ изменение самого эксперимента.

## Raw evidence и темы

`sphinx-data-viewer` оказался плохо совместим с dark mode из-за hard-coded light colors.

Принято решение **не писать vendor CSS-fix**:

- `Observed output` — stock card;
- `Actual provider code` — stock dropdown;
- `Raw captured result` — stock dropdown + обычный JSON code block/Pygments.

То есть raw evidence стало проще, стабильнее и theme-native.

## Allure performance

Реальный browser-профиль показал архитектурный дефект:

- single-file Allure HTML разросся примерно до **25.5 MiB**;
- основная причина — base64-встроенные PDF/video/image attachments.

При этом `file://` режим был важным свойством и его нельзя было ломать переходом на обычный multi-file SPA.

Решение:

- оставить Allure single-file forensic viewer;
- не дублировать в него тяжёлые media, которые уже представлены в Living Specifications;
- сохранить status/steps/labels/text evidence и быстрый direct-open.

## Масштабирование Living Specifications

Одна огромная `specifications.html` признана плохой долгосрочной моделью.

Новая структура:

- `specifications.html` — лёгкий index/health overview;
- **отдельная страница на каждый Gherkin Feature**;
- внутри Feature: Rule → Scenario → Examples/evidence;
- Feature pages не засоряют глобальный sidebar: используются как отдельные Sphinx pages с явным back-link;
- evidence/source URLs сделаны устойчивыми к вложенным путям.

Это оформлено как reusable DocOps capability и применено в пилоте.

## Следующий слой BDD

После стабилизации Living Specs начали добавлять только действительно полезные детали:

- **Implementation ↗** для каждого Given/When/Then — точная revision-pinned ссылка на реально исполненный Python binding;
- **Executable usage** — source реально исполненного `When`, чтобы показать фактический public API usage, а не вручную написанный пример;
- **Observed outcome** — короткий вывод только из явного `evidence.json("Result", ...)`, без AI-summary и heuristics;
- **Contract provenance** — graph-native REQ → TREQ/ADR/EXP/IMPL связи только там, где они реально существуют.

На живом tool-choice сценарии проверено, что Executable usage показывает настоящий `router.query(... tools, tool_choice, response_schema, max_tool_rounds ...)`, а не декоративный snippet.

## Требования пользователя

- UI не изобретать, если готовые компоненты уже решают задачу.
- Не лечить vendor/theme проблемы собственными CSS-костылями.
- Не дублировать media/evidence между Living Specs и Allure без необходимости.
- BDD должен показывать **как реально использовать capability**, но автоматически из исполненного кода.
- Любой summary должен быть детерминирован из явного evidence; никаких AI/heuristic interpretations.
- Страница должна масштабироваться по Feature, а не превращаться в бесконечную простыню.

## Точка остановки

Начат последний слой **Public contract**:

- в `py-testkit` появился `evidence.contract(name, live_object)`;
- контракт извлекается из реального Pydantic model/function/signature, а не копируется вручную.

Но renderer, массовое подключение в `llm-router`, full QA и delivery этого слоя **ещё не были завершены**.
