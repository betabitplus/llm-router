# 038 — Health Map: real geometric hierarchy принята

**Период:** 2026-09-22
**Источник:** `Продолжение работы над Sphinx -- 6ab2f032-044c-83eb-bb6c-a27a86545813.md`

## Scope

Менялась только hierarchy geometry Health Map.

Assurance semantics, source facts, layers, popup, palette и labels оставлены без изменений.

## Реальные gaps реализованы

Вместо border-симуляции весь subtree физически ужимается внутрь своего container:

- Goal получает более сильный inset;
- Feature внутри него — меньший inset;
- children больше не могут залезать обратно в gap;
- resize/redraw пересчитывает geometry без накопления inset.

Это принципиальное отличие от старого stroke-подхода:

> **gap существует в координатах layout.**

## Rounded-container artifact

Первый geometry prototype показал маленький визуальный дефект: через rounded Goal corners просвечивал Product-root background.

Product root оставили structural container/hit target, но убрали его цветную подложку из gaps.

Это дало чистый background air между Goal.

## Финальная модель

Приняты:

- заметный реальный gap между Goal;
- меньший реальный gap между Feature;
- rounded Goal/Feature containers;
- тонкие outlines вместо stroke-hacks;
- стабильная geometry при resize;
- hover/click не разрушают spacing.

Пользователь визуально принял результат; он стал финальным checkpoint этой серии итераций.

## Итоговая UX-модель Health Map

- **hierarchy = real geometry + whitespace + rounding**;
- **status = semantic red/green**, но не единственный канал структуры;
- Goal/Feature labels показываются только там, где читаются;
- никаких тяжёлых headers/panels и толстых borders;
- visual changes принимаются по реальному browser render, а не по CSS/DOM цифрам.

На этом предоставленная цепочка заканчивается принятым hierarchy checkpoint.
