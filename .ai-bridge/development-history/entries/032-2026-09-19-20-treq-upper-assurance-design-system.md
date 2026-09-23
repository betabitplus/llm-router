# 032 — TREQ Technical Assurance, верхние FEAT/GOAL/Product monitors и общий design system

**Период:** 2026-09-19 → 2026-09-20
**Источник:** `Продолжение работы над Sphinx -- 6aaec65c-1c5c-83ed-97b9-eaa218e1c02d.md`

## REQ Contract Evidence rollout завершён

- Contract Evidence создан для всех **29 parent REQ** / 15 product features.
- На момент rollout:
  - 25/29 REQ имели Verification Coverage PASS;
  - 4 честно показывали конкретные behavioral coverage gaps;
  - Fault Model оставался FAIL у всех 29, потому что required fault challenges ещё не закрыты.
- Это признано правильным состоянием: архитектура monitor-а готова, красное теперь означает реальный assurance debt, а не недоделанный UI.

## TREQ — не уменьшенная копия REQ

После изучения ISO/IEC/IEEE 29148, NASA и assurance-case подходов роли разведены:

- **REQ Contract Evidence** — доказано ли наблюдаемое продуктовое поведение.
- **TREQ Technical Assurance** — доказан ли конкретный derived/design-to constraint, который поддерживает parent REQ.

TREQ отвечает на другой бизнес-вопрос:

> зачем этот technical constraint существует, можно ли доверять его реализации и безопасно ли его менять/удалять?

Изначально были предложены отдельные `Upstream contract / Realization` PASS-блоки, но пользователь правильно заметил, что проверки вида `parent exists`, `revision matches`, `≥1 @impl` — это plumbing, а не assurance.

Финальная граница:

- traceability/revision/ownership integrity → **fail-fast validators**, не monitor;
- TREQ monitor показывает только:
  - Verification coverage;
  - Fault model;
  - History;
- parent REQ остаётся обычной навигационной ссылкой.

## First-class TREQ profiles

В Routing ветке TREQ перестали быть скрытыми criteria внутри parent REQ и получили собственные Verification Profiles/Technical Assurance pages.

Parent REQ теперь может иметь явный **Required technical support**: parent PASS зависит от нужных child TREQ, но их evidence не копируется в REQ-page.

Это сохраняет разделение:

`REQ product claim → TREQ technical support → implementation/evidence`.

## Верхние уровни assurance

Для FEAT / GOAL / PRODUCT-SYSTEM введён отдельный слой **Assurance Profiles**, не смешанный с REQ/TREQ Verification Profiles.

Принцип:

- child status сам по себе недостаточен;
- верхний уровень может требовать собственное cross/integration/validation evidence;
- если direct validation target не объявлен, monitor не придумывает его;
- не onboarded Goal = **UNKNOWN**, а не N/A, чтобы Product/System не становился ложнозелёным.

Пилот выбран на `GOAL_ROUTING_RELIABILITY`:

- cross-REQ / capability integration;
- cross-FEAT integration;
- Goal outcome validation;
- Product/System roll-up.

Добавлены только осмысленные BDD на правильном уровне; unit/property «для количества» не создавались.

## Routing vertical pilot

Использован отдельный `assurance_item`, чтобы upper-level evidence не маскировалось под REQ `coverage_item`.

Existing multi-hop sticky scenario поднят на правильный FEAT-level ownership.

Добавлены system-level scenarios через публичный `LLMRouter` и deterministic HTTP substitute:

- bounded multi-route recovery;
- rate-limit skip × normal fallback;
- degraded recovery × sticky successful route.

Living Specifications для upper assurance используют тот же BDD-document format: scenario narrative, actual interactions, executable binding, Allure evidence, technical details.

## FEAT / GOAL / Product semantics

Названия уровней закреплены:

- TREQ — **Technical Assurance**;
- REQ — Contract Evidence;
- FEAT — **Capability Assurance**;
- GOAL — **Outcome Assurance**;
- Product — **Product / System Assurance**.

Upper monitors не являются «процентом зелёных детей». Они показывают:

- support нижнего уровня;
- direct cross/integration evidence;
- outcome/validation evidence там, где оно заявлено;
- emergent/cross-goal signals на уровне Product/System.

## Общий design system вместо параллельных renderer-ов

После UI-аудита устранено дублирование между REQ/TREQ/FEAT/GOAL/Product.

Финальная архитектура:

**shared domain semantics → entity renderer → shared UI/components/shell**.

- upper renderer больше не импортирует REQ renderer;
- общие CSS/JS/shell/tiles/inspectors определены один раз;
- FEAT/GOAL/Product page generation идёт через типизированный `PageSpec` registry;
- structural guards запрещают возвращать параллельный base UI.

После refactor golden pages сохранили прежний вид, а typing/policy/security/structural gates остались зелёными.

## Новое постоянное UX-требование: навигация отдельно от monitor

В конце пользователь потребовал отдельный минималистичный hierarchy navigator.

Принято:

- навигация **не содержит PASS/FAIL** и не смешивается с assurance semantics;
- путь: `Product → Goal → Feature → Requirement → TREQ`;
- current entity выделена;
- дети показаны одной компактной ссылкой вроде `Requirements 4 ›` / `Technical support 1 ›`;
- ancestry/children берутся из существующего Sphinx-Needs graph `derives / derives_back`, без отдельной hand-written navigation model.

## Точка остановки

Навигационный дизайн выбран как hybrid breadcrumb + compact children affordance.
В source уже начат shared `navigation` projection из graph facts, но финальная реализация/QA панели ещё не завершены.
