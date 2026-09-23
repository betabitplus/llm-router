# 017 — Decision-first EXP и переход к native Living Specifications

**Период:** 2026-09-07 → 2026-09-08
**Источник:** `Восстановление контекста Sphinx Needs -- 6a9ec7ef-ebd8-83eb-9846-aa6545448e1f.md`

## Главное

- Сравнение отчётов показало:
  - **EXP** уже сильнее как человеческий инженерный рассказ;
  - **BDD/Allure** сильнее как execution browser, но хуже объясняет результат человеку.
- Для EXP принят принцип **decision-first + progressive disclosure**:
  - сверху Question → Answer → findings;
  - затем evidence;
  - raw/source/forensic детали — только глубже;
  - одна мысль должна существовать ровно в одном месте, без дублирования.
- Старый `Capability snapshot` заменён на decision-oriented findings: `Capability → Outcome → Key observation`.
- EXP UI получил:
  - кликабельные findings;
  - явные Input / Observed output;
  - единый Technical details;
  - interactive JSON tree;
  - revision-pinned provenance;
  - responsive layout и dark/light fixes.
- Для Raw result принят разумный default: автоматически раскрывать JSON до **depth=3**, глубже — вручную.
- Изменения были выпущены через DocOps и применены только к пилоту `llm-router`.

## Решение по BDD

Пользователь поставил вопрос, зачем оставлять BDD как отдельный Allure-style отчёт, если EXP стал гораздо удобнее.

После сравнения вариантов принято:

- **не переводить BDD в notebook** — notebook там был бы только лишним presentation-layer;
- source of truth остаётся **Gherkin**;
- pytest остаётся execution;
- Sphinx-Needs — traceability;
- поверх этого DocOps генерирует **native Living Specifications report** в том же UX-языке, что EXP.
- Allure временно остаётся:
  - как machine-readable evidence transport/attachments;
  - как один generic forensic test viewer.
- Специализированные Allure views `BDD stories` и `Verification by requirement` признаны дублированием native Living Specs / Verification Matrix.

Правильное разделение:

`Living Specifications → native DocOps/Sphinx human view`
`Verification Matrix → native Sphinx-Needs requirement/evidence view`
`Raw test execution → Allure forensic/debug view`.

## Living Specifications UX

Сделано:

- Feature overview / Acceptance scenarios;
- Rule как вторичный контекст;
- отдельные Scenario cards с устойчивой нумерацией;
- provider tabs только там, где это действительно examples одного Scenario Outline;
- Given / When / Then + input/output evidence;
- Technical details последним collapsed уровнем;
- deep-link из сценария в конкретный Allure test result;
- desktop light/dark и mobile QA.

Living Specifications были доведены до рабочего pilot integration.

## Требования пользователя

- Ничего лишнего и дублирующегося: **каждая мысль в единственном месте**.
- Сначала быстрое решение/состояние, затем drill-down в детали.
- Максимально использовать интерактивность, если она реально ускоряет чтение.
- Не строить второй source of truth ради красивого отчёта.
- Не тащить новый framework, если текущие данные уже достаточны.

## Важная коррекция в конце

Пользователь отверг самодельный визуальный слой: плохие spacing/typography приходилось постоянно вручную дебажить.

Принята новая граница:

- **кастомный код — только data adapter/rendering semantics**;
- **дизайн — готовые PyData Sphinx Theme + Sphinx Design components**;
- отказаться от собственного mini design system и собирать страницы из штатных cards/grids/tabs/dropdowns/badges.

На этом чат закончился: решение принято, рефакторинг Living Specs на готовые компоненты только начат.
