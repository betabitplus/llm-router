# 031 — Full Goal coverage, честный Target audit и старт Routing reliability

**Период:** 2026-09-18
**Источник:** `Продолжение работы над Sphinx -- 6aad111b-d2f4-83ed-aec6-a6e5f3fce721.md`

## Configuration принят как первый полный feature slice

После завершения mutation/provenance/qualification хвоста физически проверены все четыре Configuration Contract Evidence pages.

Итог:

- Override / Credentials / Installation — PASS;
- Invalid Configuration — честный FAIL из-за реальных verification gaps;
- all-N/A Fault Model больше не рисует пустой inspector;
- Traceability → exact Contract Evidence работает;
- один data-driven renderer обслуживает все страницы.

Configuration доказал, что pipeline масштабируется дальше одной демонстрационной страницы.

## Первый полностью пройденный multi-feature Goal: Tool orchestration

Следующим сознательно выбран небольшой, но разнообразный Goal:

Goal: `GOAL_TOOL_ORCHESTRATION`

- Feature: Tool selection
  - `REQ_TOOL_CHOICE`
- Feature: Tool execution
  - `REQ_MULTI_ROUND_TOOL_EXECUTION`
  - `TREQ_TOOL_REGISTRY`
  - `REQ_TOOL_RUNTIME_SAFETY`

Для всех parent contracts созданы Verification Profiles и Contract Evidence.

`TREQ_TOOL_REGISTRY` не получает отдельный дублирующий dashboard: его criteria входят в proof родительского Requirement.

## Tool Goal вскрыл новые infrastructure assumptions

Configuration не использовал весь спектр evidence.

Tool Choice/Multi-round показали важные новые случаи:

- VCR Replay;
- Substitute boundary;
- multiple `verifies` в одном BDD testcase;
- criterion с несколькими valid `Level × Boundary` bins;
- producer chain с VCR.

Исправлено:

- generator извлекает **все revision-pinned contract IDs**, а не только первый;
- Target parser различает не только Test Level, но и Boundary;
- Replay определяется реальным VCR `play_count`, а не target metadata;
- Substitute подтверждается runtime boundary interaction;
- Depth classification регенерируется из retained JUnit + Allure + Coverage + runtime observations;
- provenance fail-closed проверяет, что classification относится к exact retained run;
- VCR producer включён в qualification chain.

Новый Depth generator сверили с ранее принятым oracle: после исправлений не осталось semantic расхождений по Level/Boundary/Representation/M&S на общих tests.

## Tool orchestration закрыт целиком

Полный rebuild подтвердил current evidence, producer qualification, mutation freshness и structural consistency. Это стал первый доказанный **multi-feature Goal**, а не набор отдельных страниц.

## Критический Target re-audit: monitor был слишком зелёным

Пользователь специально потребовал перестать смотреть на Actual и заново определить Target **из смысла Requirements и рисков**.

Подозрение подтвердилось.

В шести из семи уже покрытых profiles Fault Model практически был implicit N/A и тем самым подгонялся под существующие tests.

Новое правило:

> Каждый profile обязан классифицировать **все project fault classes** как REQUIRED / OPTIONAL / N/A и дать rationale. Пропущенный класс — build error.

Parser сделан fail-closed:

- missing fault table;
- неизвестный/duplicate class;
- отсутствие rationale;
- неверная coverage cardinality

→ profile не собирается.

## Target стал строже, даже если monitor краснеет

После независимого аудита все 7 существующих Contract Evidence получили реальные blocking fault obligations.

Итоговая картина намеренно стала:

Итог: `Verification Coverage = PASS → Fault Model = FAIL → Overall = FAIL`

на всех 7 pages.

Это признано правильным: обычные tests подтверждают behavior, но fault resistance ещё недостаточно доказана.

## Invalid Configuration оказался сильно under-specified

Старый denominator из 5 config constraints был артефактом уже существующих TREQ/tests.

Аудит `validate_config()` выявил ещё восемь нормативных invariants, которые раньше жили только как implementation guards.

Они оформлены отдельными TREQ:

- retry wait bounds;
- route-attempt limit;
- fallback-shuffle minimum;
- tool-round limit;
- structured-output attempt limit;
- default provider declaration;
- default model/provider mapping;
- model→provider reference integrity.

Новый Target:

- Component × Local × Actual: **13 criteria / 16 required paths**;
- System public-rejection path: 1.

Mutation scope расширен со старой подвыборки до всего актуального Component contract:

**84 killed / 26 survived = 76.4%**
Component Reach 100%, Sensitivity 93.5%.

Старый 59.8% baseline признан несопоставимым из-за изменения denominator и остаётся только историей.

## Другие underfit-ы

Аудит также нашёл:

- Credentials optional-missing должен охватывать две provider families, а не одну;
- auto-rotation имеет две отдельные semantic branches;
- Config Installation требует доказать реальный subsequent runtime effect, а не только replacement object identity;
- Tool Choice требует отдельно public input forms и четыре фактически distinct serialization implementations.

Цель формируется из контракта и architecture reality, не из числа уже написанных tests.

## Следующий Goal: Routing reliability

После Configuration и Tool orchestration выбран:

Goal: `GOAL_ROUTING_RELIABILITY`

- Feature: Route fallback;
- Feature: Rate-limit-aware routing;
- 5 parent Requirements;
- derived routing/rate-limit TREQ.

Начали снова с независимого Target-аудита, а не с existing tests.

## Routing уже нашёл реальные product/tooling defects

При развитии Goal были обнаружены и исправлены реальные runtime bugs:

- sticky route semantics;
- ожидание blocked auto-key при наличии свободного credential.

Также выявлена важная mutation-attribution проблема:

`LimiterState` теперь реализует несколько sibling TREQ, поэтому старые **51% для TREQ_RATE_LIMIT_STATE** больше нельзя честно считать Requirement-specific Test Strength.

Правило:

> Mutation score допустим только для objectively single-owner implementation scope.

Shared class measurement перенесён в historical/shared diagnostic; validator запрещает повторную ложную attribution.

## Fault challenge должен быть runtime-доказан

Routing BDD уже реально инжектил HTTP 400/timeout, но старый adapter этого не видел.

Введён explicit `fault_item(contract_id, class_id)` **вместе с обязательной runtime fault-injection observation**.

Marker без наблюдаемого fault ничего не доказывает.

Monitor начал честно показывать:

- Coverage PASS;
- существующие runtime challenges — detected;
- остальные REQUIRED fault classes — missing;
- Overall FAIL.

То есть зелёный functional test не маскирует отсутствие fault-based evidence.

## Freshness mutation tooling исправлена

Найден false-fresh bug: mutation fingerprint не включал SHA самого adapter-кода и использовал неверную version constant.

Теперь fingerprint включает exact adapter SHA/version; контрольное изменение немедленно сделало старое evidence stale.

## Точка остановки

Routing semantic/verification модель уже существенно оформлена. Финальный mutation campaign оставляет только два честно attributable measured scopes:

- `REQ_INVALID_CONFIGURATION_ERRORS`;
- `TREQ_TOOL_REGISTRY`.

Но acceptance validator всё ещё содержал старые магические ожидания количества contracts/pages/measured scopes.

Последняя работа в источнике: переписать gate на **устойчивые invariants** и закончить Traceability/monitor QA.
