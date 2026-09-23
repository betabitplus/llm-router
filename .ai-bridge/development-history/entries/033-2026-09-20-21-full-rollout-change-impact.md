# 033 — Полный rollout сквозного assurance monitor и начало Change Impact

**Период:** 2026-09-20 → 2026-09-21
**Источник:** `Контекст работы Sphinx -- 6ab031e6-8cc4-83eb-8451-46fcc0445578.md`

## Health/Depth признаны обязательными и сделаны reproducible

На Sessions vertical clean build обнаружил, что **Verification Health Map** и **Verification Depth Map** раньше частично зависели от тёплого `docs/_build`.

Пользователь отдельно зафиксировал: это не legacy, а ключевые рабочие views, которые обязательно сохраняются.

Исправлено:

- обе карты строятся после clean build из authoritative Needs + retained facts;
- восстановлены scoped Allure drill-down tags;
- MTE vendor artifact больше не зависит от старого build tree;
- Health = current execution status;
- Depth = Test Level / Boundary Reality / Test Strength;
- maps остаются отдельными от Contract/Upper assurance.

Sessions vertical после этого прошёл end-to-end; REQ/TREQ ownership разделён корректно: product persistence остаётся REQ, serializer/version mechanics — TREQ.

## Rollout policy: ровно один Goal за раз

Пользователь установил рабочее правило rollout:

- выбрать **один Goal**;
- сначала честно определить Target;
- затем пройти весь Goal `Goal → Features → REQ → TREQ`;
- проверять Actual, Fault Model, navigation, Health/Depth и browser UI;
- красное не исправлять ослаблением Target;
- **следующий Goal без пользовательской проверки не начинать**;
- после каждого Goal докладывать, сколько дерева пройдено и сколько осталось.

## Последовательный rollout оставшихся Goals

### Data Safety

Техническое evidence вынесено из parent REQ в first-class TREQ.

В процессе найден реальный gap:

> исходящий request VCR редактирует, но caller-controlled content может вернуться в provider response и физически попасть в cassette.

Добавлен отдельный `TREQ_VCR_RESPONSE_CONTENT_REDACTION`; Target оставлен красным, а не подогнан под существующую sanitization.

### Tool Orchestration

Goal повторно проведён уже по финальной first-class TREQ модели.

Найден реальный gap:

> forced named tool после первого tool round превращается в generic `tool_choice="required"`, поэтому исходный named choice не гарантирован на всём multi-round workflow.

Goal Outcome Validation остаётся FAIL, несмотря на PASS нижних integration paths.

### Resilient Execution

Структура: 2 Features → 2 REQ → 4 TREQ.

Добавлены реальные sync/async recovery checks после физического disconnect.

Cross-capability и Goal Outcome validation PASS; отдельно доказан композиционный bound: retry=2 × structured=2 заканчивается после 4 provider interactions, пятого нет.

Goal overall всё равно FAIL из-за незакрытого child Fault Model debt.

### Provider Portability

Структура: 3 Features → 4 REQ → 6 TREQ.

Adapter/usage technical obligations получили собственные first-class TREQ profiles и pages; parent REQ перестали присваивать их evidence.

### Configuration

Главный ownership debt: **14 TREQ были нормативными контрактами, но их evidence всё ещё физически жило внутри parent REQ**.

Исправлено:

- 4 REQ + 14 TREQ = 18 самостоятельных Contract Evidence contracts;
- каждый TREQ имеет собственный Verification Profile, denominator, Fault Model, Actual и page;
- parent REQ агрегирует Technical Support, не копирует child proof.

### Rich Input / Output

Последний Goal проведён тем же способом.

Upper validation PASS, но overall честно FAIL:

- Structured Text provider matrix — 1/5;
- Image — 4/5;
- fault evidence по ряду contracts недостаточно.

Upper BDD не скрывает эти gaps.

## Полный rollout завершён

Финальная нормативная модель полностью прошла через сквозной monitor:

**9/9 Goals · 15/15 Features · 29/29 REQ · 34/34 TREQ = 87/87 normative nodes, 63/63 contracts.**

Это означает «monitor существует и Target/Actual связаны», а не «всё зелёное».

Независимый аудит подтвердил полноту monitor/navigation/depth связей и отсутствие false-green из-за неполных denominators. По пути исправлены реальные portal-integrity defects: битые BDD/config links, Mutation Analysis shell leakage, stale version и producer/qualification deep-links.

## Архитектура после rollout

Сквозная цепочка стала:

`Product/System → Goal → Feature → REQ → TREQ → Verification Target → retained Actual evidence → producer/confidence/freshness → fault evidence`

и обратно через navigation/Traceability Reader.

Роли остаются раздельными:

- Health — прошло ли execution сейчас;
- Depth — насколько сильное/реалистичное evidence;
- Contract Evidence — доказан ли конкретный REQ/TREQ против заранее заданного Target;
- FEAT/GOAL — доказаны ли interaction/outcome, а не просто сумма children;
- Product/System — сходится ли весь продукт.

Единый Assurance Score сознательно не вводится.

## Следующий недостающий lifecycle-layer: Change Impact / SUSPECT

После сравнения с mature V&V подходами главным следующим gap выбран:

> после изменения requirement/profile/implementation/producer — **какое retained evidence стало потенциально неактуальным и что надо перепроверить?**

Прототип использует:

`Git diff + Sphinx-Needs graph + existing fingerprints/facts`

и отдельный сигнал **SUSPECT**, не заменяющий PASS/FAIL.

Рабочая демонстрация:

`REQ_PUBLIC_API_SURFACE PASS + SUSPECT → FEAT PASS + SUSPECT → GOAL PASS + SUSPECT → Product propagated count`.

Соседние незатронутые branches SUSPECT не получают.

## Важная коррекция масштаба Change Impact

Пользователь справедливо спросил: если CI всё равно прогоняет всё, зачем этот слой?

Принято более узкое назначение:

- если cheap required evidence всегда пересчитывается на PR, SUSPECT может автоматически очищаться CI и не требует большого UI;
- основная ценность — **дорогие/выборочные проверки**:
  mutation, live/provider integration, E2E, manual validation, EXP, producer qualification и т. п.;
- Change Impact должен прежде всего быть **CI safety gate/diagnostic**:
  changed thing → affected obligations → какие required evidence ещё не revalidated.

Отдельный большой Change Impact dashboard пока не нужен.

## Точка остановки

SUSPECT оставался локальным prototype. Последний вопрос пользователя: как автоматически очистить impact для уже перепроверенного evidence и требовать точечную revalidation только там, где нового required evidence ещё нет.
