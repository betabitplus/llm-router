# 029 — От тяжёлого assurance report к строгому Requirement Monitor

**Период:** 2026-09-15 → 2026-09-17
**Источник:** `Изучи историю Sphinx -- 6aa98224-a978-83eb-9252-dbcedae0768e.md`

## Contract Evidence сначала радикально упростили

После предыдущего тяжёлого assurance report основной UX переведён на progressive disclosure:

**Overview → Evidence Frontier → Fault Detection → Evidence Trust → Assurance Gap → Evidence Paths → History → Investigate.**

Главное правило страницы:

`Possible ≠ Must ≠ Actual`
`GAP = Must − Actual`.

Тяжёлые diagnostics, raw mutants, long evidence lists и history details по умолчанию скрыты.

## Главное архитектурное исправление: Target должен жить вне monitor-а

Дальнейший аудит показал, что даже упрощённый вариант всё ещё смешивает:

- platform vocabulary;
- project verification policy;
- requirement-specific target;
- actual evidence;
- UI projection.

Принята постоянная четырёхуровневая модель ownership:

### A — Ternforge Platform

Фиксирует общую форму и semantics:

- status vocabulary;
- generic monitor components;
- test/evidence schema;
- стандартные связи и invariants.

### B — Project / Repository

Фиксирует решения конкретного проекта:

- Test Plan / Test Strategy;
- reusable Test Models;
- project thresholds;
- project-specific environment/representation classifications;
- completion criteria.

### C — Requirement

Фиксирует только то, что уникально этому contract:

- verification intent;
- required coverage items;
- applicable fault classes;
- requirement-specific criteria;
- deviations / N/A rationale.

### D — Actual Evidence

Собирается автоматически:

- pytest/JUnit;
- coverage contexts;
- mutation;
- observed interactions;
- provenance;
- producer qualification;
- freshness.

**Monitor ничего не придумывает: Target приходит из B+C, Actual из D, UI только вычисляет Status.**

Для каждой новой сущности в пилоте теперь заранее надо записывать её system level, canonical source, будущего Ternforge owner и cleanup trigger.

## Test Plan

Создан project-wide `test-plan.html` на языке ISO 29119, но без копирования generic standard boilerplate.

После нескольких cleanup-проходов там оставлены только реальные решения llm-router:

- Mutation Reach ≥80%;
- Mutation Sensitivity ≥80%;
- mutmut strength — diagnostic;
- reusable Configuration Validation Test Model;
- reusable Fault-based Test Model.

Порог 80% явно является **project decision**, а не ISO/ISTQB стандартом.

Generic Test Levels, status semantics и reusable platform vocabulary не должны копироваться в consumer Test Plan.

## Requirement-specific Verification Target

Для `REQ_INVALID_CONFIGURATION_ERRORS` создан первый полноценный Level-C target.

Примеры:

- Component × Local требует **5 semantic coverage items**, непосредственно выведенных из Statement;
- System × Local требует representative public unknown-model path с `ConfigurationError` до provider execution;
- прочие Test Levels для revision 1 могут быть честно N/A;
- fault denominator задаётся **до просмотра actual tests**, а не выводится из существующего набора evidence.

Для связи authored coverage item → execution добавлен semantic ID в JUnit property. Это устранило старую подмену:

> `4 tests passed` ≠ `4/4 required coverage items covered`.

## Требование пользователя к authoring pages

На consumer-страницах должен оставаться только **уникальный сигнал**.

Если текст без изменений поедет в другие repositories — это generic platform concern и ему не место на requirement/Test Plan странице.

Пользователь отдельно потребовал:

- минимум прозы;
- таблицы, шкалы, компактные структуры;
- корректные anchors;
- никаких названий репы, очевидных пояснений и повторов стандартной терминологии.

## Новый Requirement Monitor

После подготовки A/B/C/D старый renderer заморожен как compatibility-only.

Новый monitor получает:

- Target из Test Plan + Requirement;
- Actual из JUnit/Depth/fault evidence;
- status — только вычисляемый результат.

Первый честный результат сразу стал краснее старого UI:

- Component semantic coverage = **4/5**;
- System semantic coverage = **1/1**;
- Freshness System evidence = **UNKNOWN**.

Это считается правильным: Target больше не подгоняется под существующие tests.

## Monitor ≠ report

Несколько итераций показали, что даже новый monitor снова начал разрастаться списками, prose и forensic деталями.

Принято радикальное правило:

**Monitor — только сигналы.**

В основном слое остаются:

- общий Verification status;
- Verification matrix;
- Fault-model overview;
- evidence trust properties;
- History trend.

Не должно быть:

- test IDs;
- fault IDs;
- raw item rows;
- long semantic explanations;
- inline forensic tables;
- десятков ссылок;
- default-selected detail, который навязывает одну ветку расследования.

Семантика живёт в Requirement/Test Plan; детали — в contextual drill-down.

Дополнительные UI-инварианты, сформировавшиеся на этом monitor-е:

- пользовательский status vocabulary — **PASS / FAIL / N/A / UNKNOWN**; `N/A` приглушён, некликабелен и не блокирует overall;
- один signal — одно представление: count сравнивается с count, percentage с percentage; не дублировать одно состояние одновременно как count + percent + summary;
- tooltip объясняет конкретный signal одним коротким предложением, а не превращается в документацию;
- hash/anchor должен вести ровно к названной секции; общий verdict лучше держать sticky/pinned, чем ломать смысл anchor искусственными scroll-offset hacks.

## Verification matrix

Coverage cell должна показывать **overall evidence status**, а не один count.

Поэтому даже `System semantic coverage 1/1` может быть `UNKNOWN`, если, например, Freshness неизвестна.

Representation / Provenance / Producer qualification / Freshness / M&S признаны **свойствами конкретной evidence cell**, а не самостоятельной секцией `Evidence gates`.

Fault Model остаётся отдельным измерением, потому что отвечает другому вопросу — какие типы ошибок мы challenge/detect.

## Бизнесовые траектории чтения

Пользователь потребовал объяснять не «где поле X», а какой реальный вопрос решает monitor.

Финальная логика чтения:

- **Requirement реально обеспечен?** → overall status.
- **Проблема продукта или недостаточность проверки?** → Component/System divergence.
- **Может ли рефакторинг сломать поведение незаметно?** → mutation sensitivity.
- **Не хватает сценариев или слабые oracle/assertions?** → coverage vs detection.
- **Проверяем реальность или substitute?** → representation/boundary.
- **Можно ли доверять самому evidence?** → provenance + producer qualification.
- **Evidence относится к текущей версии?** → freshness.
- **Surrogate/model может врать?** → M&S validation.
- **Где локализован риск и достигает ли он public/system boundary?** → matrix + fault model.

Если всё зелёное, пользователь не обязан читать raw evidence.

## Точка остановки

Экспериментальная Requirement Monitor страница уже была встроена обратно в нормальный Sphinx shell и визуально проверена.

Последнее замечание пользователя осталось **не закрыто в этом источнике**:

- `Producer qualification` нужно объяснить значительно яснее на маленьком примере;
- `M&S validation = N/A` должно быть визуально приглушено;
- для Provenance / Representation / Qualification / Freshness надо явно задавать **квантор Target: ALL или ANY**, потому что иногда requirement требует, чтобы условию соответствовали все evidence paths, а иногда достаточно хотя бы одного.

То есть следующий этап — сделать evidence-confidence criteria формальными и недвусмысленными, а не только красивыми categorical statuses.
