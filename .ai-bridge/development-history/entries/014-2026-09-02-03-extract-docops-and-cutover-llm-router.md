# 014 — Выделение ternforge-tooling-docops

**Период:** 2026-09-02 → 2026-09-03
**Источник:** `Восстановить контекст Sphinx Needs -- 6a986c0c-8e08-83ed-a0f3-5c38750aab5c.md`

## Главное

- Sphinx/Needs/EXP/portal логика выросла из пилота и была выделена в отдельный репозиторий **`ternforge-tooling-docops`**.
- Зафиксировали ownership:
  - **Template** — минимальная consumer wiring;
  - **DocOps** — Sphinx extensions, graph/presentation/build logic;
  - **py-testkit** — runtime test/evidence producer integration;
  - **py-policy** — только архитектурные правила;
  - **infra-ci** — orchestration;
  - **consumer** — свои requirements/specs/experiments.
- Отдельный `docops.toml` решили не вводить без реальной необходимости.
- Evidence producer должен отдавать стандартные JUnit/Allure labels; DocOps читает их и строит graph-native views.
- Jupyter kernelspec/isolation для EXP признан инфраструктурной границей DocOps, а не обязанностью consumer scripts.
- Выпущены ранние версии DocOps **v0.2.0 → v0.2.2** и начат cutover `llm-router`.
- На конце источника 4/5 EXP были fresh; AI Studio оставался последним хвостом.

## Требования пользователя

- Consumer не должен владеть generic DocOps machinery.
- Не создавать лишний конфигурационный слой, если данные уже есть в существующем graph/config.
- Ownership должен быть чётким: каждый generic механизм живёт ровно в одном месте.
- Cutover должен удалять дублирование, а не просто подключать новый пакет поверх старого.

## Результат

DocOps стал отдельным platform-компонентом, а `llm-router` начал переход с локальной реализации на released tooling.
