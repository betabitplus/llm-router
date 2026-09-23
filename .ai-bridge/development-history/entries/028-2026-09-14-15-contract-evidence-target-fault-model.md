# 028 — Contract Evidence: Assurance Target, Guarantee Frontier и fault-model proof

**Период:** 2026-09-14 → 2026-09-15
**Источник:** `Продолжение работы над Sphinx -- 6aa85c3d-09d4-83eb-9747-15810cd97a65.md`

## Роли assurance-страниц окончательно разведены

Living Specifications очищены до **семантики**:

- что/зачем/как должно работать;
- Given/When/Then, executable usage, contract/code provenance;
- ссылки наружу на execution и assurance.

Из них убраны текущие PASS/Verified, runtime boundary, producer inventory и assurance gaps.

Роли закреплены так:

- **Health** — что сейчас прошло/сломалось;
- **Depth** — насколько глубоко/реалистично/сильно проверено;
- **Mutation Analysis** — изменения Test Strength;
- **Allure/MTE** — forensic details;
- **Contract Evidence** — почему совокупности evidence достаточно и чего ей не хватает.

## Evidence Envelope

Первый Contract Evidence строился как assurance case:

`claim → argument → evidence`.

Критический invariant:

> одна точка evidence засчитывается только тогда, когда **один конкретный evidence path** действительно достигает заявленных координат.

Нельзя склеить `System + Substitute` одного теста и `Component + Actual` другого и объявить несуществующий `System + Actual`.

Это сделало видимым важный класс false-green: Health может быть зелёным, хотя требуемой глубины/реальности доказательства нет.

## Достаточность задаёт Target, а не теоретический максимум

Главная коррекция модели:

> **«достаточно ли evidence?» определяется versioned Assurance Target / Verification Profile конкретного REQ/TREQ, а не максимально возможной картой.**

Target задаёт:

- что обязаны доказать;
- до какой boundary;
- каким evidence;
- с какими минимальными qualifiers.

Если risk/incident меняет ожидания, Target повышается новой revision, и новые gaps появляются честно.

## Guarantee Frontier

Две конкурирующие матрицы упрощены до одной основной:

**System Reach × Boundary Reality**.

Representation Fidelity становится qualifier конкретного evidence path.

Contract Evidence показывает:

- **Possible** — что можно доказать;
- **Target** — что требуется;
- **Actual** — что реально доказано;
- **GAP = Target − Actual**.

Это устраняет искусственные gaps вроде требования Direct-live там, где контракт по смыслу обязан завершиться до внешнего provider call.

## Fault-model proof

Пользователь потребовал измерять не только глубину проверки, но и **какие классы ошибок evidence способен обнаруживать**.

Для implementation mutation одного Test Strength оказалось недостаточно. Разделены:

- Mutation Reach — mutant вообще достигнут evidence;
- Mutation Sensitivity — достигнутый mutant убит;
- fault-family coverage;
- corroboration между разными verification depths.

Собственный fault classifier признан слабым источником. Для native fault metadata использован `pytest-gremlins`; `mutmut` остаётся отдельным mutation evidence source.

Важный найденный баг: mutants сначала ошибочно сопоставлялись по `(line, operator, description)`. Связь переведена на настоящий `gremlin_id`.

## Assurance History

Для истории выбран **DVC plots + Vega-Lite**, а не собственный chart framework или hosted tracker.

Историю нельзя дорисовывать задним числом. С момента появления модели должны сохраняться изменения:

- Target revisions;
- obligations/gaps;
- Reach/Sensitivity;
- survivor debt;
- fault layers;
- gap open/close;
- incidents.

## Первый честный Assurance Target

Для `REQ_INVALID_CONFIGURATION_ERRORS` authored target впервые был задан независимо от существующих тестов.

Результат оказался не полностью зелёным: один blocking gap — **Component Mutation Sensitivity 40.7% при target 80%**.

Для `TREQ_RATE_LIMIT_STATE` target соответствует его реальной технической роли; отсутствие live-provider proof не считается gap, если контракт его не требует.

Это закрепило ключевой принцип:

> **Target определяется смыслом контракта и риском, а не существующим набором evidence.**

## Evidence Paths

Каждый retained path хранит собственные qualifiers и drill-down:

- verification method/depth;
- reach/boundary;
- representation;
- producer / M&S credibility;
- freshness;
- narrative/source/raw evidence;
- mutation evidence, где применимо.

Если representativeness не доказана данными — показывается **not classified**, а не догадка.

## UX-урок

Несколько технически проходящих вариантов страницы были преждевременно названы готовыми.

Пользователь закрепил правило:

> UX-checkpoint не завершён, пока реальная browser page не соответствует согласованной структуре и не удалён лишний визуальный шум.

Тяжёлый assurance report со множеством секций постепенно признан слишком перегруженным. Сохранились смысловые блоки — frontier, qualifiers, fault model, trust, gaps, evidence paths, history/incident loop — но следующий этап должен был радикально упростить основной экран через progressive disclosure.

## Требования пользователя к UX

- быстро показывать **что возможно → что требуется → что фактически есть → где gap**;
- максимум понятного визуала, минимум текста;
- явный порядок чтения;
- детали только через hover/details/drill-down;
- semantic/health/assurance страницы не дублируют друг друга;
- честный red лучше красивого false-green.

## Точка остановки

Модель Target/Actual/Fault/Trust уже была сформирована, но основной Contract Evidence UI всё ещё считался слишком тяжёлым. Следующий этап — превратить его из assurance report в компактный monitor.
