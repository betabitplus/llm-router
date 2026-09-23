# 024 — Evidence-of-evidence завершён; Assurance UX признан перегруженным

**Период:** 2026-09-12 → 2026-09-13
**Источник:** `Восстановление контекста Sphinx Needs -- 6aa5d317-e104-83eb-9ecd-06d393f4fb17.md`

## Evidence-of-evidence доведён до production

- После предыдущего assurance slice добавлен полноценный слой **Evidence Producer → Trust basis → Calibration → Residual doubt**.
- Для high-impact producers введено правило: одного собственного теста недостаточно; нужен усиленный trust basis.
- Реальные pilot examples:
  - Google GenAI fake SDK;
  - Gemini WebAPI fake SDK;
  - по две qualification records;
  - EXP_0002 / EXP_0003 используются именно как **calibration**, не как regression verification.
- `Trust state` вычисляется из graph evidence, а не хранится вручную как `trusted=true`.
- Verification narrative получил прямой drill-down:
  `verification → producer → Evidence Trust → qualification/calibration`.
- Generic producer schema/semantics подняты в shared owners и протянуты через template acceptance; в `llm-router` оставлены только product-specific producer instances и реальные qualification/calibration records.
- Проведены adversarial checks на missing/broken qualification, producer links и calibration.

Shared owner-chain была полностью протянута до `llm-router`; public portal подтвердил producer → trust basis → calibration → residual doubt end-to-end.

## Zero-tail после повторного аудита

Повторный аудит нашёл важный test-design хвост: docs-only key-rotation workaround позволял двум logical slots использовать один secret и тем самым мог давать ложную уверенность. Его заменили на deterministic сценарий с реальным `LLMRouter`, реальным HTTP adapter, localhost endpoint и двумя различными demo credentials — без provider secrets.

## Главный новый вывод: data model правильный, human UI — нет

После того как пользователь впервые реально прошёл опубликованный портал, **Verification Assurance Map и Evidence Trust были отвергнуты как нечитаемые**.

Проблема:

- наружу почти напрямую выведена внутренняя assurance-модель;
- один простой вопрос превращается в Path / Execution envelope / Boundary interaction / producers / raw proof / gaps / code dump;
- одни и те же факты повторяются разными словами.

Принято трёхуровневое представление:

1. **Reader:** что доказываем → чем → насколько далеко → что осталось.
2. **Drill-down:** конкретная проверка и observed proof.
3. **Deep audit:** producer qualification/calibration, raw execution, code, Allure.

Evidence Trust — **не основной путь чтения**, а аудит второго порядка.

## Универсальная модель reliability

Пользователь потребовал верхний язык, который подходит не только llm-router, а 3D engine, spacecraft, mobile app, calculations и т. п.

От линейной самодельной шкалы `logic → real request` отказались: она не универсальна.

После сверки NASA / ISO / ISTQB принят standards-aligned каркас:

### 1. System scope

`Component → Integration → System → End-to-end / Acceptance`

### 2. Environment fidelity

`Controlled → Representative → Operational`

### 3. Verification method

`Test / Analysis / Demonstration / Inspection`

### 4. Evidence trust

Отдельно показывает надёжность самого evidence/process/tooling.

Пятый вывод вычисляется:

**Next gap — что осталось до максимальной уверенности.**

Проценты confidence признаны нежелательными: они создают ложную точность. Верхний слой должен показывать положение по независимым осям, а domain-specific детали — ниже.

## Требования пользователя

- На первом экране должно быть возможно за секунды понять надёжность проверки.
- Внутренняя кухня pytest/Allure/JUnit/producers не должна торчать наверху.
- Нужны компактные visual signals, шкалы и progressive disclosure вместо текста.
- Верхняя модель должна быть универсальной и standards-aligned, не привязанной к Google/provider-specific терминологии.
- Если единого официального стандарта нет, прямо так и писать — не выдавать synthesis за стандарт.
- Существенный UX-redesign сначала согласовывать в лёгком псевдографическом/mockup виде: содержание и порядок чтения должны быть понятны до реализации.

## Зафиксированный design note

Универсальная модель записана в betabit-notes:

`ternforge/docs/research/0026-define-universal-verification-reliability-view.md`

Там сохранены две шкалы, четыре вопроса, Method, Evidence Trust и Next gap. Это research synthesis, а не объявленный новый официальный стандарт.
