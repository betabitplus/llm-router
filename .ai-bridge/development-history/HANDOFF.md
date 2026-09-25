# Handoff — Sphinx / DocOps / Assurance Portal

Этот файл — **стартовая точка для нового владельца работы**.

Он не заменяет repository state и не заменяет историю 001–043. Его задача — передать то, что новому человеку опаснее всего потерять: **ментальную модель, принятые границы, инварианты, UX-требования и выученные уроки**.

> История фиксирует, как решения менялись.
> Репозиторий показывает, что существует сейчас.
> Этот handoff объясняет, **почему система сейчас устроена именно так и что нельзя случайно сломать**.

______________________________________________________________________

## 0. Ориентация за 5 минут

Если нужно быстро включиться в работу, достаточно сначала понять десять вещей:

01. **Sphinx-Needs — authoritative engineering graph.** Не строить второй graph/source of truth.
02. **REQ = product WHAT, TREQ = technical obligation, Verification/Assurance Profile = HOW prove it.**
03. **Target проектируется до просмотра Actual.** Красный monitor допустим; false-green — нет.
04. **Runtime fact сильнее marker/AST/inference.** Actual нельзя дорисовывать из Target.
05. **Evidence path — отдельная единица proof.** Multiple paths нельзя схлопывать в один test.
06. **Health, Depth, Contract Evidence и Living Specs отвечают на разные вопросы.** Не сливать их обратно в один dashboard.
07. **Mutation/fault evidence — отдельная сила доказательства.** Contract-specific mutation score допустим только при однозначном implementation ownership.
08. **Change Impact уже встроен во Freshness.** Видимый lifecycle signal — STALE; отдельный SUSPECT удалён.
09. **Monitor = сигналы, не журнал.** PASS/FAIL/N/A/UNKNOWN, counts, progressive disclosure; forensic детали глубже.
10. **Pilot scope дисциплинирован.** Reusable logic идёт правильному owner, но rollout других consumers не начинается без отдельного решения.

Текущая принятая точка UX: Health Map использует multilayer assurance projections, а hierarchy читается через **real geometry + whitespace + rounding**, не через толстые borders.

Если времени мало, после этого файла прочитать:

- [**033** — полный assurance rollout](entries/033-2026-09-20-21-full-rollout-change-impact.md);
- [**034** — финальная Freshness / Change Impact модель](entries/034-2026-09-21-change-impact-per-evidence-freshness.md);
- **035–038** — текущее направление и принятый UX Health Map; ссылки собраны в [README](README.md);
- [**039** — Health Map v2 и ревизия честности монитора](entries/039-2026-09-23-health-map-v2-monitor-honesty-audit.md);
- [**040** — лента слоёв по критичности и таблица всех слоёв](entries/040-2026-09-24-health-map-layer-strip-severity-table.md);
- [**041** — круговой Overall, причины провалов, разметка вне квалификации](entries/041-2026-09-24-health-map-radial-overall-causes-markup-split.md);
- [**042** — Depth Map на рендерере Health Map и одна карта на две страницы](entries/042-2026-09-24-25-depth-map-one-shared-map.md);
- [**043** — Verification Map: здоровье и меры на одной карте, виды на карточке слоя](entries/043-2026-09-25-26-verification-map-views-on-card.md);
- нужный тематический диапазон из раздела «Как читать историю по теме» ниже.

______________________________________________________________________

## 1. С чего начинать работу

Перед любым изменением:

1. Открыть живой `llm-router` и связанные owner-repositories; не считать этот handoff снимком текущего HEAD.
2. Сверить текущую implementation с последними relevant history records.
3. Определить, к какому уровню относится изменение:
   - product semantics;
   - verification target;
   - evidence production;
   - assurance aggregation;
   - presentation/navigation.
4. Исправлять проблему **в правильном owner-layer**, а не локальным workaround в consumer.
5. После изменения проверять не только tests, но и те derived views/facts, чьи inputs реально изменились.

Исторические counts, test totals и release versions намеренно не являются каноном. Они полезны только как контекст конкретного решения.

______________________________________________________________________

## 2. Где система остановилась

По последнему принятому checkpoint:

- полный normative graph был проведён через assurance pipeline;
- REQ/TREQ/FEAT/GOAL/Product имеют раздельные assurance semantics;
- retained evidence имеет per-path provenance/freshness;
- mutation/fault evidence интегрированы без подмены обычных tests;
- Change Impact встроен в Freshness, отдельного SUSPECT-status больше нет;
- Health Map стал whole-system projection нескольких assurance dimensions;
- hierarchy Health Map визуально решена через **real geometry + whitespace + rounding**, а не через толстые borders.
- Health Map и Depth Map — одна карта с общим runtime; они различаются только тем, что Health судит, а Depth измеряет (042).
- Прототип Verification Map сводит здоровье и меры на одной карте; виды слоя живут на его открытой карточке. Решение, заменит ли она две карты, не принято (043).

Последний принятый UX checkpoint Health Map:

> **hierarchy = real geometry / whitespace; status = semantic red/green; визуальная структура не должна зависеть только от цвета.**

Это принятая точка, а не приглашение снова перепроектировать карту с нуля.

______________________________________________________________________

## 3. Главная модель системы

Authoritative engineering graph — **Sphinx-Needs**.

Нормативная и доказательная цепочка:

`Product/System → Goal → Feature → REQ → TREQ → Verification/Assurance Target → executable evidence → retained evidence → confidence/freshness/fault proof`.

Обратный путь тоже должен существовать:

`test / implementation / evidence → contract → Feature → Goal → Product`.

### Нормативные уровни

- **GOAL** — желаемый outcome.
- **FEATURE** — capability.
- **REQ** — observable product contract: **WHAT** должно быть истинно.
- **TREQ** — derived/design-to technical constraint, поддерживающий REQ.
- **Verification Profile** — **HOW** конкретный REQ/TREQ должен быть доказан.
- **Assurance Profile** — cross/integration/outcome validation для FEAT/GOAL/Product.
- **Executable test/evidence** — Actual, а не источник нормативного Target.

Ключевой принцип:

> **Verification не имеет права изобретать product semantics.**

Если правило нормативно — оно должно жить в REQ/TREQ, а не появляться впервые внутри test plan/profile/monitor.

______________________________________________________________________

## 4. Самый важный invariant: Target независим от Actual

Это один из главных уроков всей работы.

Нельзя:

1. посмотреть, какие tests уже существуют;
2. собрать из них Target;
3. получить зелёный monitor;
4. назвать это assurance.

Правильный порядок:

`Requirement / risk → Target → tests/evidence → Actual → comparison`.

Поэтому красный monitor — нормален, если реальная доказательная база слабее честно заданного Target.

### Monitor ничего не придумывает

- **Target** приходит из Project/Test Plan + Requirement/TREQ Verification Profile.
- **Actual** приходит из retained runtime evidence.
- **Status** вычисляется сравнением.
- UI только показывает результат.

Особенно важно:

> **Actual никогда не должен восстанавливаться из Target metadata.**

Это уже приводило к false-green.

______________________________________________________________________

## 5. Что является evidence truth

Приоритет источников:

> **captured runtime fact > explicit authored declaration > source/AST inference**.

AST/source inference допустим как fallback или presentation enrichment, но не должен подменять runtime fact, если факт можно захватить при execution.

Примеры:

- Replay определяется фактическим VCR replay/runtime observation, а не названием test/marker.
- Substitute/participant/fidelity подтверждается runtime boundary observation.
- Hypothesis/property execution подтверждается runtime evidence.
- Fault challenge считается только если есть соответствующее runtime observation, а не один marker.
- Implementation reach берётся из Coverage.py per-test contexts, когда это возможно.

______________________________________________________________________

## 6. Evidence path — единица assurance

Один criterion может иметь **несколько retained evidence paths**.

Например один Scenario Outline может дать provider-specific paths.

Нельзя схлопывать их в один случайный testcase или перезаписывать последний.

Для path могут отдельно существовать:

- Test Level / System Reach;
- Boundary;
- Representation;
- Provenance;
- Producer chain;
- Producer qualification;
- Freshness;
- M&S validation;
- source/runtime links;
- mutation/fault evidence.

### Quantifiers

Условия могут логически требовать ALL/ANY, но UI должен по возможности показывать **реальный denominator**, а не абстрактный текст вроде “ALL paths”.

Примеры:

- `4/5 required evidence`;
- `4/4 retained paths`;
- `N/N model paths`.

______________________________________________________________________

## 7. Reach, Reality и M&S — разные вещи

Нельзя смешивать:

### System Reach

Насколько много реальной системы участвовало в проверке.

### Boundary / Representation Reality

Что реально находилось за важной boundary: actual / representative / surrogate / synthetic и т. п.

### M&S Validation

Насколько доказано, что surrogate/model адекватно представляет referent для intended use.

M&S level вычисляется из графа, а не вписывается руками: L2 — только при калибрующем EXP с валидным отчётом капсулы. Цель L0 значит «не требуется», а не PASS.

Высокий M&S level **не превращает surrogate в actual**.

И наоборот, глубокий system-level test может использовать surrogate dependency.

Test type (`Unit / Integration / BDD / E2E / Property`) — это не автоматический уровень глубины и не fidelity score.

______________________________________________________________________

## 8. Evidence Producer и qualification

Verification tooling само может дать false-green.

Поэтому producer qualification означает не “нам нравится этот инструмент”, а:

> **есть executable evidence, что producer/collector/importer не превращает ошибочный результат в корректное доказательство.**

Для critical producer одного “у него есть свои tests” может быть недостаточно.

Qualification может включать:

- false-green controls;
- golden/fixture cross-check;
- comparison с независимым implementation;
- comparison с real referent;
- retained live/EXP calibration.

M&S/calibration и producer qualification — связанные, но разные вопросы.

В пилоте квалификация привязана к отпечатку инструментов и кода, который вычисляет факты (билдер, мониторы, domain, registry, implementation faults, harness, `tests/conftest.py`), и сравнивается целиком. Правка любого из этих файлов делает всех производителей UNKNOWN, и Evidence quality краснеет с причиной «Unqualified producer», пока не перезапущен `qualify-evidence-confidence.py`. Разметка карт живёт в `assurance_map_pages.py` вне отпечатка: вид правится без переквалификации (история 041).

______________________________________________________________________

## 9. Fault Model и mutation

Functional PASS не означает, что контракт достаточно защищён от ошибок.

Нужно отдельно различать:

- **какие fault classes обязаны быть challenged**;
- какие действительно challenged;
- какие detected;
- насколько assertions/oracle чувствительны к ошибочным изменениям.

### Mutation

Полезные понятия:

- Mutation Reach — мутированный код достигнут связанным evidence.
- Mutation Sensitivity — достигнутый mutant убит.
- Test Strength — killed / (killed + survived) среди covered valid mutants.

Mutation score допустим как contract-specific signal **только при объективно однозначном ownership implementation scope**.

Если class/function реализует несколько sibling contracts — нельзя приписывать один общий mutation score одному из них. Лучше N/A/shared diagnostic, чем ложная точность.

Implementation fault classes (`impl.comparison` / `impl.boundary` / `impl.control-flow`) считает одна кампания pytest-gremlins по всем контрактам с `@impl`; класс detected, только если пойманы все его attributable mutants. Каждый mutant обязан выполняться полноценным pytest: lightweight runner gremlins фабрикует kills на fixture/param/BDD tests (история 039).

Mutants не становятся Allure test cases.

Роли:

- Depth Map — слой Mutants caught: доля пойманных attributable-мутантов текущей кампании implementation faults по контракту (история 042);
- Mutation Analysis — journal/work queue;
- MTE/raw report — mutant forensic detail;
- Allure — реальный pytest execution.

______________________________________________________________________

## 10. Freshness и Change Impact

Отдельный `SUSPECT` status был исследован и **удалён**.

Финальная модель:

`evidence → exact inputs → fingerprint → CURRENT / STALE`.

- CURRENT — нормальное состояние и в UI обычно не показывается.
- STALE — retained evidence больше не соответствует текущим inputs и блокирует required assurance.
- Change Impact — внутренний dependency calculation, определяющий affected evidence.

Inputs должны быть per-evidence, а не один глобальный snapshot репозитория.

Snapshot входов действителен, только если снят в начале именно удержанного прогона; probe/pytest-сессии инструментов не имеют права его перезаписывать.

Используются фактические зависимости:

- test source;
- executed production code;
- REQ/TREQ;
- Verification/Assurance Profile;
- Gherkin;
- harness;
- cassette/data;
- mutation config/adapter/input.

CI должен переснимать всё, что умеет автоматически. После этого stale остаётся только там, где required evidence действительно ещё не получено.

Не нужны ручные категории “cheap/heavy” как новая taxonomy.

______________________________________________________________________

## 11. Разделение пользовательских views

Это принципиально. Не превращать всё обратно в один гигантский dashboard.

### Living Specifications — semantics

Отвечает:

- что делает capability;
- какие scenarios;
- как выглядит executable usage;
- какой public contract;
- какой observed outcome.

Human-facing Living Specification должна читаться без знания pytest и внутренних framework/API деталей. Строгая BDD-семантика обеспечивается tooling, а не пользовательскими соглашениями.

Не должен дублировать operational PASS/FAIL, producer internals и assurance diagnostics.

### Verification Health Map — текущее состояние

Отвечает:

- где система сейчас PASS/FAIL;
- какие branches затронуты;
- позволяет быстро провалиться в нужный contract/raw execution.

Позже карта стала переключать несколько canonical projections (Overall/Execution/Coverage/Faults/Evidence/Assurance), но остаётся overview, а не forensic report.

Слои — одна лента с прокруткой: Overall первой, проваленные по числу провалов, прошедшие в исходном порядке за линией «ок»; все слои сразу — таблица «All layers», скрытая по умолчанию (история 040).

Overall — круг: вердикт в центре, кольца иерархии, кольцо контрактов и по кольцу на слой; каждый луч — один контракт через все слои. Каждый слой называет причины своих провалов, у вида есть адрес `#слой:ID`, страницы контрактов, целей и способностей ведут на своё место на карте, карточки показывают изменения с прошлого удержанного прогона (история 041).

### Verification Depth Map — сила/глубина evidence

Отвечает:

- до какого уровня тестов доходят собственные тесты контракта (Test level);
- с чем они говорят на границе системы: ничего, substitute, запись или живой сервис (Boundary);
- насколько проверены модели за substitutes и записями (Model validation, L0–L4);
- какую долю мутантов своего кода ловят его тесты (Mutants caught).

Depth измеряет, а не судит: последовательные шкалы без красного и зелёного, Overall — лучи через кольца уровней, таблица контрактов вторым режимом (история 042).

### Две карты — одна карта

Health Map и Depth Map запускают один общий runtime `mapPage` из `assurance_map_pages.py`: виды, лента слоёв, All layers, Filters, таблица, карточка, Find, адрес, клавиши, Changes и раскладка у них общие. Страница только описывает свои слои: цвета, что слой говорит о метке, тело карточки, фасеты, кольца, колонки таблицы. Различия допустимы только смысловые: Health судит, Depth измеряет. Гейт проверяет, что страницы не собирают общие части сами (история 042).

### Verification Map — прототип

`verification-map.html` складывает обе карты (`pairsMap` из фабрик `healthMap` и `depthMap`): лента — шесть слоёв Health, меры Depth — виды тех слоёв, на чей вопрос они отвечают (Coverage — Test level и Boundary, Fault model — Mutants caught, Evidence quality — Model validation, Overall — Depth и таблица). Своей Sphinx-страницы и навигации пока нет (история 043).

### Contract Evidence / REQ monitor

Отвечает:

> доказан ли конкретный observable REQ против заранее заданного Target?

### TREQ Technical Assurance

Отвечает:

> доказан ли technical obligation, который поддерживает parent REQ?

TREQ — не маленькая копия REQ и не страница “parent exists / revision matches”.

Graph/schema integrity — validator concern.

### FEAT Capability Assurance

Проверяет composition/cross-REQ capability claims.

### GOAL Outcome Assurance

Проверяет outcome и cross-FEAT validation, если такой target существует.

### Product / System Assurance

Показывает product-level composition, cross-goal/emergent/operational signals.

### Allure

Остаётся mature forensic execution backend.

Не нужно снова строить собственный generic test execution browser.

### Engineering Experiments

EXP — observation/decision evidence, а не normative `Verified`.

EXP может калибровать producer/model, но experiment result не становится regression verification автоматически.

______________________________________________________________________

## 12. Ownership между repositories

Долговечное правило:

> **Пилот проверяется в llm-router, но reusable implementation живёт сразу у правильного owner. Заморожен rollout других consumers, а не shared infrastructure.**

Базовая граница:

- **py-testkit** — test mechanics, runtime capture, reusable test helpers/producers;
- **DocOps** — assurance semantics, evidence ingestion/interpretation, rendering facts/views;
- **infra-ci** — orchestration, artifacts, Pages/dossier invocation; не знает внутренности Sphinx renderer;
- **template-components / template-py-library** — реальный generated default и acceptance;
- **llm-router** — product semantics, product-specific targets/profiles/evidence instances;
- **Sphinx-Needs** — authoritative graph.

Generic capability должна пройти:

`owner tooling → template acceptance → generated consumer acceptance → llm-router pilot`.

Но не надо самовольно начинать rollout остальных consumers.

______________________________________________________________________

## 13. Scope discipline

Это повторяющийся урок.

Несколько раз работа технически “логично” уходила дальше согласованного scope и потом полностью откатывалась.

Правило:

> **“Продолжай” означает продолжать текущую принятую задачу, а не автоматически начинать следующую roadmap phase.**

Особенно опасно:

- преждевременно переносить локальный prototype в platform;
- делать release/rollout до пользовательской приёмки UX;
- расширять работу на fleet consumers;
- превращать исследовательский spike в production architecture без отдельного решения.

Если текущая задача — локальный prototype, shared repos не трогаются. Для такого prototype ведётся короткий ledger: временный механизм → будущий owner при принятии → cleanup trigger при отказе.

______________________________________________________________________

## 14. UX-инварианты

Пользовательские требования здесь очень устойчивы.

### Monitor — только сигнал

Не превращать monitor в journal/report.

Основной слой:

- PASS / FAIL / N/A / UNKNOWN;
- counts;
- compact tiles/scales;
- weakest blocking signal;
- минимальный navigation/drill-down.

Не основной слой:

- test IDs;
- mutant IDs;
- длинные списки;
- code dump;
- raw JSON;
- большие evidence tables;
- повторяющаяся explanatory prose.

### Progressive disclosure

Первый экран должен быстро отвечать на вопрос.

Детали уходят в:

`overview → selected signal → drill-down → forensic/raw evidence`.

Виды слоя на картах — тоже progressive disclosure: они живут на открытой карточке слоя; при трёх видах и больше карточка открывается на полтора вида с «+N», повторный клик сворачивает; Overall всегда раскрыт целиком (043).

### Статусный язык

Использовать:

- PASS
- FAIL
- N/A
- UNKNOWN

Не возвращать MET/NOT MET.

N/A визуально приглушён, некликабелен и не блокирует PASS/FAIL.

### Один signal — одно представление

- count сравнивается с count, percentage — с percentage;
- не показывать один и тот же статус одновременно несколькими эквивалентными числами/виджетами;
- tooltip — одно короткое предложение о конкретном signal, не мини-документация;
- hash/anchor ведёт точно к названному блоку; общий verdict держится sticky/pinned, а не достигается искусственным scroll-offset.

### Не дублировать мысль

Один факт должен иметь одно canonical место.

Если информация уже существует в canonical evidence page, другой view лучше ссылается на неё, чем копирует.

### Navigation ≠ monitor

Hierarchy navigation:

- не содержит PASS/FAIL;
- показывает ancestry/current/compact children;
- строится из authoritative Needs graph;
- не становится вторым tree dashboard.

______________________________________________________________________

## 15. UI / design lessons

### Сначала согласовать сложный UX

Если меняется информационная архитектура или порядок чтения, сначала согласовать content/read-flow лёгкой псевдографикой или mockup в чате и только затем кодировать. Это дешевле повторных UI-переделок и помогает отделить проблему данных от проблемы presentation.

### Не строить mini frontend framework без необходимости

Был большой custom JS/CSS слой для Living Specs/EXP — его признали ошибкой.

Граница:

- custom code — data adapter / semantics, если действительно нужен;
- presentation — по возможности PyData Sphinx Theme, Sphinx Design, Sphinx-Needs, MyST/Pygments и готовые компоненты.

Не лечить vendor/theme проблемы собственным большим CSS fork, если можно заменить проблемный widget штатным primitive.

### Browser QA обязателен

DOM existence / computed CSS / HTTP 200 недостаточны.

Реально найденные классы ошибок:

- неправильные Allure deep-links;
- hydration;
- Plotly SVG scaling;
- hover меняет spacing;
- dark mode;
- overflow;
- misleading hierarchy.

### Health Map hierarchy

Пройдено несколько неудачных решений:

- hierarchy только оттенком status color — недостаточно;
- тяжёлые Goal panels/header bands — перегружают;
- толстый stroke как “gap” — выглядит как жирная рамка;
- микрошрифт — запрещён.

Принято:

- real geometric insets/gutters;
- whitespace;
- rounded containers;
- thin outlines;
- Goal/Feature labels только если помещаются;
- status color и hierarchy используют **разные визуальные каналы**.

### Карты не прыгают и не врут о переходе

- Treemap раскладывается один раз по ширине страницы; боковая панель только сужает плитки, кольца только сдвигаются.
- Все виды одной высоты; легенда держит высоту самого высокого вида; переключатель Rings/Table и счётчик стоят на одном месте во всех видах.
- Карточка называет, куда ведёт клик, словами целевой страницы — заголовком страницы и раздела; гейт сверяет эти названия с настоящими страницами (история 042).
- Легенда — одна строка во всех видах, остальное за «+N»; строка видов на узкой странице есть всегда; жирное начертание выбранного вида не меняет ширину; слайдер складывается сразу и с той же скоростью, что раскрывается (043).
- Анимировать исключения, а не норму: редкий провал привлекает внимание медленным кольцом и янтарной обводкой, а где проваливается многое, ничего не движется (043).
- Вид, которому под фильтрами нечего показать, не прячется, а бледнеет и объясняет почему (043).

______________________________________________________________________

## 16. Что сознательно НЕ вводили

Не возвращать без новой причины:

- второй requirements/graph engine рядом со Sphinx-Needs;
- единый Assurance Score / confidence percentage;
- собственный generic execution browser вместо Allure;
- notebook как presentation-layer для BDD;
- собственный experiment tracker для редких heterogeneous EXP;
- огромный Change Impact dashboard;
- отдельный persisted SUSPECT state;
- ручную taxonomy cheap/heavy evidence;
- Requirement-specific mutation score для shared implementation scope;
- duplicate REQ/TREQ dashboards с одинаковой семантикой;
- automatic inference, который выдаёт UNKNOWN за PASS;
- четвёртый вид Health Map сверх круга, карты и таблицы, зум и фильтры по статусу, графики истории на мониторе (041);
- ряд вкладок видов под лентой или на панели легенды; превью вида при наведении; удержание слайдера закрываемой карточки до ухода курсора с ленты (043).

Если одно из этих решений хочется вернуть, сначала перечитать соответствующую историю и объяснить, какое новое ограничение делает прежнее решение больше невалидным.

______________________________________________________________________

## 17. Как читать историю по теме

Не обязательно читать 001–043 подряд.

### Foundations / почему вообще Sphinx-Needs

Читайте **006–010**.

### Portal UX / Living Specifications / EXP

Читайте **011–019**.

### Deep coverage / assurance case / evidence-of-evidence

Читайте **019–025**.

### Mutation / Test Strength / fault model

Читайте **026–031**.

### Requirement Monitor / Verification Profiles / Target vs Actual

Читайте **028–031**.

### TREQ / FEAT / GOAL / Product assurance

Читайте **032–033**.

### Freshness / Change Impact / selective revalidation

Читайте **033–034**.

### Health Map multilayer semantics и финальный hierarchy UX

Читайте **035–038**, затем **039–043**.

### Ownership / scope mistakes

Особенно **015, 021, 026, 027**.

______________________________________________________________________

## 18. Как понять, что новое изменение сделано правильно

Перед завершением meaningful change проверить:

- Изменение живёт у правильного owner?
- Не появился второй source of truth?
- Target сформирован независимо от Actual?
- Actual происходит из retained/runtime evidence, а не target metadata?
- Не потерялись multiple evidence paths?
- Reach / Boundary / Representation / M&S не смешаны?
- Producer qualification основана на evidence, а не декларации?
- Fault Model denominator не подогнан под существующие tests?
- Mutation attribution действительно однозначна?
- Изменившееся retained evidence корректно стало STALE?
- Healthy CURRENT не создаёт UI noise?
- Верхний уровень не копирует evidence детей вместо собственного claim?
- Navigation не содержит assurance statuses?
- Monitor показывает signal, а не journal?
- Реальный browser UI проверен глазами?
- Не начался новый scope/rollout без явного решения?

Если на любой вопрос ответ сомнительный — лучше остановиться и сначала разобраться с моделью.

______________________________________________________________________

## 19. Что считать хорошим продолжением

Хорошее продолжение этой работы обычно выглядит так:

1. выбрать конкретный engineering/user problem;
2. определить его уровень и owner;
3. сформулировать invariant/Target до implementation;
4. использовать существующий graph/evidence model;
5. добавить минимальный новый signal;
6. специально попытаться получить false-green;
7. проверить real browser UX;
8. только после принятия — generalize/propagate.

Плохое продолжение:

- добавлять новые dashboards “на всякий случай”;
- увеличивать taxonomy без конкретного решения, которое она улучшает;
- красить монитор зелёным под текущие tests;
- дублировать одну и ту же truth в нескольких страницах;
- решать owner-level defect локальным consumer hack;
- считать технически зелёный gate эквивалентом пользовательской приёмки.

______________________________________________________________________

## 20. Последнее замечание

В истории есть один недоступный исходный чат: **023 / 6aa5498d…**. Его содержание намеренно не было реконструировано по соседним разговорам.

Все остальные записи — condensed history: там сохранены решения и уроки, а операционный шум специально удалён.
