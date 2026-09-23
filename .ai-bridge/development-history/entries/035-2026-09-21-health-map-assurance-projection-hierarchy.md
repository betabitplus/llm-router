# 035 — Verification Health Map становится whole-system assurance projection

**Период:** 2026-09-21
**Источник:** `Продолжение работы над Sphinx -- 6ab1a423-303c-83eb-9e33-e9a902f7e1ef.md`

## Старые system maps очищены

Старые `Specification Map` / `Specification Health` убраны из normal portal navigation.

Ключевыми system views остаются:

- **Verification Health Map**;
- **Verification Depth Map**.

## Главная проблема старой Health Map

Старая Health Map фактически отвечала только:

> все связанные tests прошли?

После полного assurance rollout это стало вводить в заблуждение: execution мог быть зелёным, хотя Contract Evidence честно FAIL по coverage, fault model, evidence trust или technical support.

Поэтому Health Map начали превращать в **whole-system projection canonical assurance facts**, а не execution-only heatmap.

## Шесть слоёв одной карты

Одна treemap переключает независимые projections:

1. **Overall** — canonical verdict соответствующего monitor;
2. **Execution** — retained tests + upper scenarios;
3. **Coverage** — required proof targets/scenarios;
4. **Faults** — required fault groups;
5. **Evidence** — Representation / Provenance / Producer qualification / Freshness / M&S;
6. **Assurance** — TREQ support и upper support/integration/validation.

Семантика берётся из уже существующих monitor facts; отдельный второй assurance engine не создаётся.

`N/A` исключается из denominator, missing/UNKNOWN/stale/unqualified required signal не становится green.

## UI

Принцип:

> **одна карта, несколько смысловых слоёв**, а не отдельный dashboard на каждый вопрос.

Сверху — компактные tabs с PASS/FAIL и counts.

Hover показывает только полезную цифровую выжимку и lineage; forensic детали остаются глубже.

На самой карте оставлены только **Goal/Feature labels**. REQ/TREQ/Product text убран как шум; длинные названия режутся, а не уменьшаются до микрошрифта.

## Важный Plotly-урок

Одинаковый CSS font-size не гарантировал одинаковый визуальный размер: Plotly сам масштабировал часть SVG labels.

Исправление:

- Plotly не масштабирует Goal/Feature text;
- clipping/truncation выполняется нашим кодом;
- если normal-size label не помещается — он скрывается.

Это закрепило правило: UI проверяется **глазами на реальном render**, а не только по DOM/CSS значениям.

## Иерархия оказалась отдельной perceptual-проблемой

Одних оттенков внутри PASS/FAIL color оказалось недостаточно: Goal и Feature визуально воспринимались как равноправные соседние cells.

Попытки через shelf/band, borders, padding и keylines либо почти не помогали, либо перегружали карту.

Главный вывод:

> **status и hierarchy нельзя кодировать одним визуальным каналом.**

Status остаётся semantic red/green, а parent-child hierarchy должна в первую очередь читаться геометрией/layout.

## Точка остановки

Функциональная multilayer Health Map уже существовала, но hierarchy visualization ещё не была принята. Следующий этап — найти лёгкий способ визуально отделять Goal и Feature без тяжёлых panels/headers и без усиления цветового шума.
