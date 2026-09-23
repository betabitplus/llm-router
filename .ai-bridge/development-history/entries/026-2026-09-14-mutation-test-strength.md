# 026 — Test Strength через mutation testing

**Период:** 2026-09-14
**Источник:** `Продолжай обзор проекта -- 6aa71f0e-2284-83ed-a373-0050985707e1.md`

## Сначала исправлена ошибка scope

В начале чата работа самовольно съехала из **локального Depth Map prototype** в productionization py-testkit/DocOps.

Пользователь это остановил.

Преждевременную productionization полностью откатили. Продолжение снова ограничено **локальным prototype + ручной browser QA**, без релизов/rollout.

Это повторно закрепило правило: даже технически логичное продолжение нельзя начинать вместо явно согласованной текущей задачи.

## Depth/Credibility prototype завершён

Связь Representation Fidelity ↔ Producer Credibility доведена до рабочего вида:

- producer hover/click подсвечивает affected contracts;
- reverse-link Requirement → producer;
- credibility details свернуты под картой;
- low-credibility signal компактный и не конкурирует с основной fidelity coloring;
- impact учитывает direct + contract roll-up.

## Какие ещё объективные свойства силы тестов искать

После обзора NASA/NIST/Google/Microsoft выделены перспективные направления:

- **Fault Detection Sensitivity** — заметит ли suite ошибку;
- **Behavioral Challenge Coverage**:
  - input/configuration combinations;
  - state/sequence coverage;
  - boundary/off-nominal cases;
  - failure modes / load / concurrency;
- structural branch/condition/MC/DC coverage — supporting signal, не главный depth axis.

Не вводить искусственные L0–L4, пока есть прямые измерения.

Первым выбран **mutation-based Test Strength**, потому что он наиболее автоматизируем и объективно измеряет качество assertions/oracle.

## Test Strength

Использована общепринятая mutation-testing семантика:

**Test Strength = killed / (killed + survived) среди covered valid mutants.**

Важно не путать с обычным Mutation Score:

- Mutation Score штрафует также непокрытый код;
- Test Strength отвечает более чисто: **если код уже выполняется связанными тестами, заметят ли они ошибочное изменение?**

Для requirement-level оценки:

`REQ/TREQ → linked tests → реально исполненный implementation slice → mutations → killed/survived`.

Критическое ограничение spike:

> mutation scope должен быть **однозначно attributable конкретному contract**.

Один `@impl` на целый файл недостаточен, если файл реализует несколько обязанностей. Неоднозначные случаи должны оставаться **N/A**, а не получать ложную цифру.

## Реальный local spike

Через `mutmut` измерены реальные contracts:

- `REQ_INVALID_CONFIGURATION_ERRORS`: 61 killed / 41 survived → **59.8%**;
- `TREQ_RATE_LIMIT_STATE`: 51 / 49 → **51.0%**;
- `TREQ_TOOL_REGISTRY`: 28 / 3 → **90.3%**.

Test Strength добавлен третьей проекцией Depth Map.

## Правильный mutation investigation UX

Самодельный блок `Mutation testing · local spike` признан временным и удалён.

Исследование mutmut / Cosmic Ray / PIT / Stryker привело к разделению:

- **mutmut** — Python mutation execution engine;
- **Mutation Testing Report Schema** — standard retained mutation artifact;
- **Mutation Testing Elements (MTE)** — готовый detailed UI;
- Depth Map — только contract-level Test Strength projection;
- Allure — подробности настоящего pytest execution, не mutants.

Правильный flow:

`Requirement → Test Strength Map → MTE Mutation Analysis → exact mutant/source line → pytest → exact Allure result`.

Не превращать mutants в Allure test cases.

Локальный pilot сформировал реальные scoped mutants и standard mutation-report artifact; `coveredBy` строится из Coverage.py per-test contexts, а если точную связь доказать нельзя, поле остаётся пустым.

Raw truth:

- Allure results — execution evidence;
- Coverage.py contexts — test→line;
- mutation-report.json — raw mutation truth;
- `verification-test-strength-facts.json` — только projection для карты.

## Практические правила mutation testing

Из опыта Google/PIT/Stryker:

- не мутировать весь проект на каждый commit;
- использовать diff/requirement-scoped runs в PR и более широкие периодические audits;
- survivors важнее глобального score: они должны быть actionable;
- фильтровать equivalent/uninteresting mutations, logging/generated/glue noise;
- учитывать timeout/flaky/incompetent statuses отдельно.

## Точка остановки

Архитектура локального mutation flow уже собрана, но последний end-to-end путь **Depth Map → measured contract → MTE → exact Allure** ещё не был полностью принят. В production/shared tooling ничего из этого ещё не переносилось.
