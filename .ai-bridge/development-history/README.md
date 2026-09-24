# История разработки Sphinx / DocOps

Короткие хронологические записи по развитию Ternforge → llm-router → Sphinx-Needs / DocOps.

## Передача работы

**Новый владелец начинает с [HANDOFF.md](HANDOFF.md).**
Там собраны текущая ментальная модель, ownership, ключевые invariants, роли views, UX-правила, сознательно отвергнутые подходы и checklist перед изменениями. История 001–041 нужна уже как объяснение, **почему** эти решения появились и как они менялись.

## Что сохраняем

Только то, что важно для продолжения работы:

- принятые архитектурные и продуктовые решения;
- ключевые факты и изменения состояния системы;
- требования, пожелания и ограничения пользователя;
- важные отклонённые подходы и причины смены направления;
- границы ownership/scope;
- релизы только когда они фиксируют значимый этап.

Не сохраняем обычную хронику работы, команды, длинные списки проверок, повторные подтверждения и промежуточный шум.

## Формат

Записи идут по исходной хронологии. Поздняя запись может отменять или уточнять раннее решение — ранняя остаётся как история изменения направления.

Если exact source недоступен, это отмечается отдельной записью; соседний контекст не подставляется вместо отсутствующего чата.

## Структура

- `HANDOFF.md` — актуальная ментальная модель и правила продолжения работы.
- `entries/` — хронологические development-history records; поздняя запись может уточнять или отменять раннюю.

## Записи

01. [001 — Проектирование пилота Living Specifications](entries/001-2026-08-23-24-llm-router-living-specifications-pilot-design.md)
02. [002 — Реализация пилота Living Specifications](entries/002-2026-08-25-living-specifications-pilot-implementation.md)
03. [003 — Завершение пилота и доказательство публикации](entries/003-2026-08-25-pilot-completion-release-pages-proof.md)
04. [004 — Удаление старого verification/E2E framework](entries/004-2026-08-25-26-remove-verification-e2e-framework-friction.md)
05. [005 — Zero-tail аудит после cleanup](entries/005-2026-08-26-zero-tail-cleanup-audit.md)
06. [006 — Переход к requirements-driven engineering graph](entries/006-2026-08-26-27-requirements-driven-engineering-graph.md)
07. [007 — Закрытие старой фазы Living Specifications](entries/007-2026-08-27-close-old-living-specifications-phase.md)
08. [008 — Первый Sphinx-Needs foundation pilot](entries/008-2026-08-27-28-sphinx-needs-foundation-first-pilot.md)
09. [009 — Reader/tooling слои и release dossier](entries/009-2026-08-28-post-pilot-tooling-release-dossier.md)
10. [010 — Полное завершение traceability-пилота llm-router](entries/010-2026-08-28-29-complete-llm-router-traceability-pilot.md)
11. [011 — Переработка engineering portal в читаемый интерфейс](entries/011-2026-08-29-30-engineering-portal-ux-redesign.md)
12. [012 — Требования, ADR и Engineering Experiments](entries/012-2026-08-30-09-01-requirements-adrs-engineering-experiments.md)
13. [013 — Provider-level Engineering Experiment capsules](entries/013-2026-09-01-02-provider-experiment-capsules-v0.15.1.md)
14. [014 — Выделение ternforge-tooling-docops](entries/014-2026-09-02-03-extract-docops-and-cutover-llm-router.md)
15. [015 — Завершение DocOps cutover и жёсткая граница scope](entries/015-2026-09-03-docops-pilot-template-cleanup-scope-boundary.md)
16. [016 — Доведение DocOps ownership до zero-tail состояния](entries/016-2026-09-05-07-docops-ownership-zero-tail.md)
17. [017 — Decision-first EXP и переход к native Living Specifications](entries/017-2026-09-07-08-exp-living-specs-reporting.md)
18. [018 — Удаление custom UI, Feature pages и enrichment BDD evidence](entries/018-2026-09-08-09-upstream-ui-feature-pages-bdd-enrichment.md)
19. [019 — Завершение BDD enrichment, EXP provenance и план Product Assurance](entries/019-2026-09-09-10-bdd-exp-product-assurance-plan.md)
20. [020 — Deep specification coverage и semantic-first portal](entries/020-2026-09-10-deep-coverage-semantic-portal.md)
21. [021 — Traceability Reader, Health Map и проект Verification Assurance](entries/021-2026-09-10-11-reader-health-assurance-design.md)
22. [022 — Assurance infrastructure vertical slice и Verification Assurance Map](entries/022-2026-09-11-12-assurance-infrastructure-map.md)
23. [023 — Источник недоступен: 6aa5498d…](entries/023-source-unavailable-6aa5498d.md)
24. [024 — Evidence-of-evidence завершён; Assurance UX признан перегруженным](entries/024-2026-09-12-13-evidence-trust-universal-reliability.md)
25. [025 — Verification Health/Depth Maps и Evidence Producer Credibility](entries/025-2026-09-13-verification-health-depth-credibility-maps.md)
26. [026 — Test Strength через mutation testing](entries/026-2026-09-14-mutation-test-strength.md)
27. [027 — Mutation workflow и разделение semantics / health / assurance](entries/027-2026-09-14-mutation-workflow-and-evidence-separation.md)
28. [028 — Contract Evidence: Assurance Target, Guarantee Frontier и fault-model proof](entries/028-2026-09-14-15-contract-evidence-target-fault-model.md)
29. [029 — От тяжёлого assurance report к строгому Requirement Monitor](entries/029-2026-09-15-17-requirement-monitor-test-plan.md)
30. [030 — Verification Profiles и масштабирование Contract Evidence на Configuration](entries/030-2026-09-17-18-verification-profiles-configuration-slice.md)
31. [031 — Full Goal coverage, честный Target audit и старт Routing reliability](entries/031-2026-09-18-full-goal-target-audit-routing.md)
32. [032 — TREQ Technical Assurance, верхние FEAT/GOAL/Product monitors и общий design system](entries/032-2026-09-19-20-treq-upper-assurance-design-system.md)
33. [033 — Полный rollout сквозного assurance monitor и начало Change Impact](entries/033-2026-09-20-21-full-rollout-change-impact.md)
34. [034 — Change Impact объединён с per-evidence Freshness](entries/034-2026-09-21-change-impact-per-evidence-freshness.md)
35. [035 — Freshness принят; Health Map становится whole-system assurance projection](entries/035-2026-09-21-health-map-assurance-projection-hierarchy.md)
36. [036 — Health Map: hierarchy через whitespace и единый visual system](entries/036-2026-09-21-22-health-map-whitespace-design-system.md)
37. [037 — Health Map: толстая рамка не равна настоящему gap](entries/037-2026-09-22-health-map-real-gaps-vs-stroke.md)
38. [038 — Health Map: real geometric hierarchy принята](entries/038-2026-09-22-health-map-geometric-hierarchy-shipped.md)
39. [039 — Health Map v2 и ревизия честности монитора](entries/039-2026-09-23-health-map-v2-monitor-honesty-audit.md)
40. [040 — Health Map: лента слоёв по критичности и таблица всех слоёв](entries/040-2026-09-24-health-map-layer-strip-severity-table.md)
41. [041 — Health Map: круговой Overall, «почему красное» и разметка вне квалификации](entries/041-2026-09-24-health-map-radial-overall-causes-markup-split.md)
