# 008 — Первый Sphinx-Needs foundation pilot

**Период:** 2026-08-27 → 2026-08-28
**Источник:** `Восстановление контекста Ternforge -- 6a906722-db04-83ed-833c-17a045001cf2.md`

## Главное

- Реализован минимальный foundation для связки **requirements → implementation → tests/evidence**.
- `py-testkit` получил trace/evidence integration.
- JUnit начали импортировать в Sphinx через Sphinx-Test-Reports и связывать с Needs.
- Для реализации использовались CodeLinks и revision-aware ссылки.
- В CI ввели генерацию/проверку evidence так, чтобы документация строилась из фактических test results, а не из hand-written статусов.
- Foundation проверяли через generated template consumer и затем в `llm-router`.
- Во время пилота нашли и исправили реальные consumer/tooling defects.
- `llm-router` дошёл до релиза **v0.12.0**.

## Требования пользователя

- Сначала доказать **минимально необходимый foundation**, не строить сразу огромный portal/framework.
- Связи должны быть машинно проверяемыми и revision-aware.
- Статусы тестов должны приходить из реального исполнения.
- Любая platform-функция должна проверяться не только unit-тестом tooling, но и реальным consumer path.

## Результат

Sphinx-Needs впервые стал рабочим source-of-truth graph для requirements и текущего evidence в `llm-router`.
