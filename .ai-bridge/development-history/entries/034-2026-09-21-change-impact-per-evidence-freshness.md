# 034 — Change Impact объединён с per-evidence Freshness

**Период:** 2026-09-21
**Источник:** `Продолжение работы над Sphinx -- 6ab12c07-6a2c-83eb-a952-1bc7b0d7a776.md`

## Отдельный SUSPECT оказался лишним

Изначально обсуждалась схема:

`change → SUSPECT → revalidation`

и даже ручные категории AUTO / ON_DEMAND / MANUAL.

От этого отказались как от лишней taxonomy.

Финальная модель:

- **Change Impact** вычисляет, какие evidence затронуты изменением;
- **Freshness** сравнивает retained fingerprint конкретного evidence с его текущими inputs;
- отдельного persisted/status `SUSPECT` нет;
- `CURRENT` — нормальное состояние и в UI молчит;
- `STALE` — единственный видимый сигнал неактуального required evidence и blocking condition.

## Per-evidence Freshness

Старый freshness был слишком грубым: общий snapshot захватывал слишком большую часть репозитория, поэтому локальное изменение могло сделать stale множество несвязанных contracts.

Freshness переведён на **конкретный evidence/path**.

Inputs определяются автоматически из уже имеющихся фактов:

- test source;
- реально исполненный production code через Coverage.py contexts;
- REQ/TREQ;
- Verification/Assurance Profile;
- Gherkin;
- harness;
- cassette/data;
- mutation inputs/fingerprints.

Ручной mapping `file → test` не вводится.

## Selective revalidation доказан end-to-end

На реальном изменении production code система показала правильное поведение:

1. обычный retained pytest переснял затронутое test evidence;
2. старое mutation evidence осталось STALE;
3. structural gate заблокировался только на соответствующем contract/mutation proof;
4. selective mutation runner выбрал только этот scope;
5. после rerun fingerprint обновился и gate снова прошёл.

Главный итог:

> **CI не обязан повторять весь дорогой verification stack; он перепроверяет только evidence, inputs которого реально изменились.**

## Mutation runner

`mutmut` не добавляется в обычные project dependencies из-за dependency conflict.

Runner использует isolated ephemeral `uv --with mutmut` environment.

Также исправлен lifecycle defect: mutation engine должен импортироваться только после подготовки его временного config/workspace.

## UI

Freshness намеренно тихий:

- healthy CURRENT не рисуется;
- STALE показывается только на непосредственно затронутом contract/proof;
- отдельный SUSPECT не распространяется на FEAT/GOAL/Product;
- Traceability Reader не получает новый lifecycle-status;
- fake TTL не используется.

Если Overall FAIL по другой причине, Freshness её не маскирует.

## Важные edge cases, найденные при реализации

- generated `__pycache__` не должен входить в fingerprints и создавать массовый false-STALE;
- upper-monitor qualification обязана учитывать ту же freshness semantics;
- selective mutation campaign нельзя валидировать правилом «последний campaign всегда full»;
- UI-regression не должен требовать отображать healthy CURRENT.

## Итог

Change Impact не исчез — он стал **внутренним dependency calculation существующего Freshness**, а не новой пользовательской сущностью.

Механизм был проверен end-to-end: exact inputs → STALE → selective revalidation → CURRENT, без demo-state в финальном portal.
