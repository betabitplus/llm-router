# 030 — Verification Profiles и масштабирование Contract Evidence на Configuration

**Период:** 2026-09-17 → 2026-09-18
**Источник:** `Продолжение работы над Sphinx -- 6aabf65a-9260-83ed-83c4-a75dfbf01582.md`

## Evidence confidence: от ALL/ANY к понятным denominators

Последний вопрос предыдущего чата про «все paths или хотя бы один?» сначала оформлен как формальный Target vocabulary **ALL / ANY**.

Это важно на уровне модели: Requirement действительно может потребовать, чтобы условию соответствовали все evidence paths или хотя бы один.

Но в UI `ALL items / ALL paths` оказалось слишком абстрактным и смешивало разные множества.

Финальный визуальный язык стал конкретнее:

- Semantic coverage → **4/5 required evidence**;
- Representation → **4/4 retained paths**;
- Provenance → **4/4 retained paths**;
- Producer qualification → **4/4 retained paths**;
- Freshness → **4/4 retained paths**;
- M&S → только **N/N model/surrogate paths**.

Внутренняя quantifier-policy сохраняется, но пользователь видит реальный denominator.

## M&S исправлен концептуально

M&S больше не отдельный равноправный gate.

Он физически вложен в **Representation** и включается только для actual evidence path, использующего surrogate/model.

Исправлен настоящий logic bug: применимость M&S раньше определялась по **target representation**, теперь — по каждому фактическому retained path.

Правила:

- Actual path → M&S N/A;
- Surrogate path + достаточный M&S target/evidence → PASS;
- Surrogate path без объявленного M&S target → UNKNOWN/blocking;
- N/A визуально не конкурирует с PASS/FAIL.

## Единый status vocabulary

`MET / NOT MET` заменены на более простой и единый язык:

**PASS / FAIL / N/A / UNKNOWN**.

Это становится общим языком monitor-а.

## Fault-model UX

Fault group показывает отдельно:

- Required classes;
- Challenged;
- Detected;
- detection effectiveness;
- mutation checks, где применимо.

Важно различать:

- **coverage fault classes** — какие обязательные виды дефектов вообще challenge;
- **detection effectiveness** — насколько evidence ловит уже challenged faults.

Optional/EXTRA evidence не влияет на PASS/FAIL и не должно занимать основной monitor layer.

## Requirement очищен до нормативного WHAT

При дальнейшей ревизии выяснилось, что Verification Target всё ещё фактически создавал product semantics внутри verification layer.

Например `timeout > 0` не должен рождаться из test plan.

Принята новая separation-of-concerns модель:

### Requirement

Только нормативное поведение + rationale.

`REQ_INVALID_CONFIGURATION_ERRORS` поднят до revision 2 и формулирует общий публичный контракт отказа до provider execution.

### TREQ

Конкретные normative engineering constraints:

- `TREQ_CONFIG_PROVIDER_IDENTITY`;
- `TREQ_CONFIG_MODEL_DECLARATION`;
- `TREQ_CONFIG_REQUIRED_BASE_URL`;
- `TREQ_CONFIG_ATTEMPT_TIMEOUT`;
- `TREQ_CONFIG_RETRY_ATTEMPTS`.

Verification больше не изобретает эти правила.

## Новый отдельный слой: Verification Profile

Contract-specific **HOW to verify** вынесен из Requirement в:

`docs/verification-profiles/`.

Verification Profile владеет:

- Test Level / Boundary / Representation target;
- verification criteria;
- evidence aggregation;
- fault applicability;
- blocking mutation checks.

Test Plan остаётся выше как reusable project strategy/model.

Итоговая authoring chain:

`Test Plan`
→ `Requirement / TREQ`
→ `Verification Profile`
→ `Executable tests`
→ `JUnit / Allure / coverage / runtime observations`
→ `Contract Evidence monitor`
→ `Mutation Analysis forensic detail`.

## Стабильные Verification Criteria

Старые IDs вида `component:unknown-model` удалены как implementation-coupled.

Введены стабильные semantic `VC_*`:

- `VC_CONFIG_PROVIDER_IDENTITY`;
- `VC_CONFIG_MODEL_DECLARATION`;
- `VC_CONFIG_REQUIRED_BASE_URL`;
- `VC_CONFIG_ATTEMPT_TIMEOUT`;
- `VC_CONFIG_RETRY_ATTEMPTS`;
- `VC_INVALID_CONFIGURATION_PUBLIC_REJECTION`.

Test связывается двумя независимыми отношениями:

- `verifies(...)` → какой нормативный REQ/TREQ он доказывает;
- `coverage_item(...)` → какой criterion Verification Profile он удовлетворяет.

Изменение test implementation/type/path не требует переименовывать semantic criterion.

## Freshness boundary обновлён

Перенос verification design в отдельную директорию потребовал добавить:

`docs/verification-profiles/**/*.md`

в run-start verification inputs.

Теперь изменение Verification Profile делает retained evidence **STALE**.

Adapter также перестал искать verification tables в Requirement docs и читает только canonical verification-profile layer.

## Configuration как первый настоящий vertical slice

После одной принятой страницы пользователь попросил проверить универсальность на целой feature-area, а не клонировать шаблон вслепую.

Выбран **Configuration**.

Подготовлены четыре parent Contract Evidence:

- `REQ_REQUEST_OVERRIDE_PRECEDENCE`;
- `REQ_INVALID_CONFIGURATION_ERRORS`;
- `REQ_CREDENTIAL_RESOLUTION`;
- `REQ_CONFIG_INSTALLATION_COHERENCE`.

Derived TREQ не получают дублирующих dashboards: их proof входит criteria parent Requirement.

Renderer переделан из hardcoded single-requirement в data-driven multi-profile.

## Реальный product-test defect

Configuration slice нашёл слабый test у `REQ_CONFIG_INSTALLATION_COHERENCE`.

Раньше он по сути делал:

`get_config() → install_config(тот же объект)`.

Это не доказывало обещание установки **новой** configuration и последующего runtime behavior.

Тест исправлен:

- distinct replacement snapshot;
- новый `RouterRuntime` захватывает replacement;
- cache invalidation проверяется при реальной замене.

## Масштабирование вскрыло системные assumptions

Configuration slice доказал, что инструменты ещё не были универсальными.

### 1. Двойная классификация evidence

Depth правильно видел Override BDD как:

`System Integration × Substitute × Surrogate · M&S L0`.

Monitor ошибочно выводил:

`System × Substitute × Actual · M&S N/A`.

Причина — настоящий SUT ошибочно принимался за Actual representation внешнего participant.

Решение:

> **Verification Depth classification становится единственным canonical source для Reach / Boundary / Representation / M&S.**

Monitor не вычисляет вторую классификацию.

### 2. Provenance не обобщился

Новые criteria были PASS, но provenance INCOMPLETE из-за parser/join assumptions первого profile.

Gate не ослабляли; исправляли source-of-truth logic.

### 3. Hypothesis producer не был qualified

Property evidence использовал `PRODUCER_HYPOTHESIS`, но qualification record отсутствовал.

Правильный результат был UNKNOWN, а не ложный PASS.

Добавлена настоящая intended-use qualification/false-green control; producer registry дошёл до **9/9 QUALIFIED**.

### 4. All-N/A Fault Model

Если у Requirement нет обязательных fault classes, Fault Model должен быть **N/A и не блокировать overall**, а не UNKNOWN.

### 5. Traceability routing

`Contract evidence →` показывается только профилированным contracts и ведёт на их реальную страницу.

## Состояние к концу источника

После owner-level исправлений новые Configuration paths получили корректные provenance/freshness/classification; три новые Contract Evidence страницы стали PASS, а Invalid Configuration остался FAIL из-за **реальных известных gaps**, а не инфраструктуры.

Но изменение tests сделало mutation campaign `REQ_INVALID_CONFIGURATION_ERRORS` **STALE**.

Новый full mutation rerun упал внутри prototype harness, который скрывал stdout/stderr `mutmut`.

## Точка остановки

Осталось диагностировать mutation failure, переснять fresh campaign и закончить физическую QA всех Configuration Contract Evidence страниц. До этого slice намеренно не считался финально принятым.
