# 027 — Mutation workflow и разделение semantics / health / assurance

**Период:** 2026-09-14
**Источник:** `Продолжение работы над Sphinx -- 6aa7f385-c678-83eb-9785-95965bb2b130.md`

## Локальный mutation checkpoint принят

Финально проверен физический путь:

`Depth Map → Test Strength → contract → Mutation Testing Elements → exact pytest/Allure`.

- сохранено 233 реальных scoped mutants;
- неоднозначные implementation scopes честно остаются N/A;
- producer highlighting, light/dark, overflow и reset повторно проверены;
- production/shared tooling не менялся.

## Mutation testing превращён из эксперимента в связный workflow

После повторного обзора Google / PIT / ArcMutate / Stryker / mutmut / Cosmic Ray принято:

- `mutmut` остаётся Python execution engine;
- standard Mutation Testing Report Schema — retained artifact;
- Mutation Testing Elements — detailed investigation UI;
- Allure — execution evidence конкретного pytest;
- Test Strength — requirement-level projection, а не глобальный vanity score.

Главный operational signal — не «mutation score ниже X», а **новый необъяснённый survivor в изменённом contract**.

## Локальный llm-router pilot

Всё делалось только в `llm-router`, с будущими owners/cleanup triggers в `.ai-bridge`.

Последовательно добавлены:

- provenance/freshness: campaign metadata и impl/test/config fingerprints; изменение делает старое evidence stale;
- changed-contract mode: `git diff → implementation scope → contract → linked tests → mutmut`;
- baseline/delta: стабильный campaign identity, New / Existing / Resolved и auditable suppression;
- Mutation Analysis как штатная Sphinx/PyData work queue;
- operator feedback о полезности/cost без преждевременной фильтрации operators;
- structural closure на всём pilot contract set.

## Повторная ошибка scope и её полный откат

После завершения локального pilot работа снова преждевременно пошла в platform extraction через py-testkit / infra-ci / py-policy / DocOps.

Полезные технические выводы были получены, включая важный dependency conflict: `mutmut 3.8` требует новый `click`, несовместимый с текущей DocOps/sphinx-codelinks цепочкой; spike доказал isolated `uv` overlay как возможное решение.

Но пользователь повторно уточнил правило:

> сначала полностью принять живую фичу в llm-router; перенос generic частей в платформу — только после отдельного разрешения.

Premature platform implementation полностью откатили. В `.ai-bridge` оставили только **post-pilot ownership notes** и явную фиксацию: learnings retained, но platform implementation ещё не существует.

## Финальный пользовательский flow mutation tooling

После UX-cleanup роли разделены:

- **Verification Depth Map** — основной монитор; Test Strength details живут в hover самой карты.
- **Mutation Analysis** — только журнал/очередь: New, Debt, Stale, история New → Resolved.
- **Raw mutants / MTE** — forensic drill-down до конкретной мутации source.
- **Allure** — конкретный test execution/evidence.
- лишний `Test Strength watch` удалён как дублирование карты.

Обычный путь:

`Monitor → Journal → Raw mutant / Allure`.

## Assurance отделён от mutation flow

Ссылка на Verification Assurance внутри mutation workflow признана ошибкой.

Естественный audit-flow:

`Traceability Reader → Contract Evidence`.

Contract Evidence должен отвечать только на вопрос:

Вопрос: «Почему мы считаем этот Requirement/TREQ доказанным и насколько сильна совокупность evidence?»

Он не должен быть ещё одним health/dashboard экраном.

## Новый фундаментальный порядок ответственности

Пользователь отдельно потребовал очистить Living Specifications и остальные страницы от смешения трёх разных задач:

1. **Semantics** — что/зачем/как должно работать.
   Living Specs и semantic docs; могут ссылаться на raw status, но не дублируют PASS/Verified, Verification Boundary и producer internals.

2. **Execution health** — что реально прошло сейчас.
   Health Map, Allure, journals.

3. **Assurance / confidence** — почему evidence достаточно и где остаются дыры.
   Contract Evidence / assurance views.

## Следующее направление: Evidence Matrix / evidence envelope

Для assurance не нужен один confidence score или «пирамида».

Исследование GSN/CAE, requirement verification matrices и NASA/INCOSE V&V привело к более подходящей модели:

- X: **System Reach**;
- Y: **Representation Fidelity**;
- в ячейках — реальные evidence;
- qualifiers: **Test Strength**, **Producer Credibility**, diversity методов.

Так сразу видно, например: есть `system + synthetic` и `component + live`, но отсутствует `system + live`.

Такая матрица должна существовать для конкретного REQ/TREQ и затем консервативно агрегироваться на Feature/Goal.

## Точка остановки

Разделение responsibilities и целевая Evidence Matrix были **только исследованы и сформулированы**. Реализация нового Contract Evidence / evidence envelope ещё не началась.
