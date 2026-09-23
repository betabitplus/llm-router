# 025 — Verification Health/Depth Maps и Evidence Producer Credibility

**Период:** 2026-09-13
**Источник:** `Summarise architecture work -- 6aa698db-1ac4-83ed-850a-dd5f8257ac54.md`

## Verification Health Map

Старую «Specification Map», окрашенную runtime-статусом, переосмыслили как отдельный operational view:

**Verification Health Map = что сейчас реально работает?**

- иерархия остаётся `Goal → Capability → Requirement/TREQ`;
- цвет отражает фактический результат последнего retained run;
- health считается DocOps из authoritative Sphinx-Needs graph + current-revision evidence, **не из Allure**;
- hover показывает реальные `passed / failed / missing` по verification type;
- failure/missing поднимается вверх по hierarchy;
- click ведёт в **ровно соответствующий набор raw results в Allure**.

Для Allure сделан deterministic mapping всех **117/117 pytest nodeids → Allure result IDs**. Для крупных веток используются derived scope-tags в собранном report, поэтому каждый из 68 map nodes открывает только свои tests, а не весь inventory. Эти tags — навигационная projection, не новый source of truth.

Allure по умолчанию раскрывает дерево через его штатный `expandedTrees`, без автокликов/мерцания.

Верх карты превращён в одну компактную status bar, которая не растёт по высоте при добавлении новых verification types; tested даже с большим числом synthetic layers.

## Verification Depth Map

Следующий отдельный вопрос:

**насколько глубоко мы вообще проверили контракт?**

Первоначальную `Environment: Controlled → Representative → Operational` ось пользователь отверг как мало полезную для software без production environment.

После исследования модель уточнена до независимых измерений:

### Test / System Reach

Показывает, сколько системы реально участвовало в проверке.

Финальная локальная шкала прототипа:

`Component → Component integration → System → System integration`

### Representation Fidelity

Показывает, что было за внешней границей:

`Synthetic / Abstract → Surrogate / Simulated → Representative → Actual`

Ключевое правило: **Test Level и Fidelity независимы**. Можно иметь глубокую system integration с VCR/fake или узкую component integration с реальной зависимостью.

Типы тестов Unit/Integration/Property/BDD остаются evidence contributors и не превращаются в уровни глубины.

Goal/Capability roll-up консервативный: уровень ветки определяется слабейшим descendant contract, а не самым сильным тестом внутри.

## Правда карты должна быть доказана

Пользователь отдельно потребовал не доверять визуализации самой по себе.

Источник каждого уровня был перепроверен по `117 tests`:

`nodeid → source test → runtime observations / coverage / boundary facts → derived reach/fidelity`.

Главное правило осталось прежним:

**captured runtime fact > explicit declaration > source/AST inference**.

Нельзя раскрашивать карту по имени директории `integration/e2e` или по label теста.

## Evidence-to-evidence / M&S

Для surrogate evidence исследовали NASA M&S Validation `L0…L4`.

Важное разделение:

- **Representation Fidelity** — насколько реальным был участник/заменитель;
- **M&S Validation** — насколько доказано, что surrogate адекватно представляет referent.

Не использовать формулу вроде `L3 ⇒ Representative`: оси связаны, но не эквивалентны.

Для validation records предложена детерминированная логика:

- L1 — intended use / conceptual basis;
- L2 — сравнение с real referent;
- L3 — покрыты критичные поведения intended use и evidence достаточно свежее;
- L4 — практически вся заявленная область применения подтверждена.

Уровень должен вычисляться из structured evidence, а не задаваться вручную.

## Важная UX-коррекция

Попытка сделать M&S третьей treemap-проекцией оказалась неправильной: большинство requirements получили N/A и карта ничего полезного не рассказывала.

Принято:

- treemap оставляет **Test Level** и **Representation Fidelity**;
- M&S переносится в отдельный **Evidence Producer Credibility** view, потому что credibility относится к producer/model, а не к requirement.

Текущий pilot показал реальный trust gap:

- Scripted HTTP — L0, большой impact;
- VCR — L0, большой impact;
- Google fake SDK — L2 через EXP_0002;
- Gemini fake SDK — L2 через EXP_0003.

Сверху показывается не абстрактный score, а конкретный impact вроде:

**63 tests · 23 contracts rely on L0 producers**.

## Связь Depth Map и Producer Credibility

Это не три независимых виджета:

`Requirement → evidence → Test Level + Representation Fidelity → если Surrogate → Producer → Credibility L0…L4`.

Принята интеграция:

- Requirement hover на Fidelity показывает producer + Lx;
- click по producer подсвечивает все зависимые contracts;
- surrogate с низкой credibility получает тонкий warning outline, **не меняя основной fidelity color**;
- impact считается direct + contract roll-up, чтобы цифры producer совпадали с реально подсвеченной картой.

## Требования пользователя

- Никаких искусственных общих confidence scores.
- Уровни и цвета должны быть понятны слева направо от слабого к сильному.
- Status/hover — короткие, полезные, один смысл на строку; никаких дублирующих legends.
- Любая карта должна быть вручную проверена в браузере: hover, click, overflow, lag, dark theme.
- Не переносить prototype в DocOps, пока UX/semantics не приняты.

## Точка остановки

Health Map и Depth/Credibility были рабочими **локальными прототипами**. Последним принятым изменением стала связка producer → affected contracts + low-credibility warning на Fidelity map; во время ручной проверки ещё исправлялся direct+roll-up impact count.
