# 019 — Завершение BDD enrichment, EXP provenance и план Product Assurance

**Период:** 2026-09-09 → 2026-09-10
**Источник:** `Восстановление контекста Sphinx Needs -- 6aa1a6e9-d764-83eb-81b2-4f21bb464df1.md`

## BDD enrichment завершён

- BDD enrichment был доведён до released py-testkit/DocOps integration.
- Living Specifications теперь показывают:
  - exact Executable usage реально исполненного pytest-bdd binding;
  - revision-pinned Implementation links;
  - **Public contract** из живых Pydantic schemas/functions;
  - Observed outcome;
  - Raw result;
  - Contract provenance из Sphinx-Needs;
  - Technical details и точный Allure deep-link.
- Реальный consumer integration выявил два дефекта:
  - inherited multiline docstring Pydantic ломал generated RST;
  - fully-qualified Python name обрезался на mobile.
    Оба исправлены в owner-layer, без CSS-костылей.
- Consumer integration был опубликован и проверен.
- Отдельный аудит подтвердил: **Allure оставляем** как mature forensic execution backend. Удаление заставило бы писать собственный pytest event/evidence transport и generic execution browser.

## Решение по EXP tooling

Пользователь попросил проверить, нужен ли EXP аналог Allure/experiment tracker.

Зафиксирована важная семантика:

- TEST/BDD может быть `Passed/Verified`;
- EXP **не должен называться Verified**: он хранит наблюдение и вывод, а не подтверждает нормативный контракт.

Исследованы MLflow/W&B/DVC/Sumatra/noWorkflow/jupyter-cache/Quarto и другие варианты.

Итог:

- **Quarto не нужен** — Sphinx/MyST-NB/Sphinx Design уже закрывают presentation.
- **Sumatra не подходит**: почти не заменяет наши EXP invariants и добавляет собственную DB/config; causal freshness для untracked capsule inputs он не закрывает.
- Остальные trackers слишком тяжёлые для редких heterogeneous experiments.
- Текущий подход признан нормальным **research-compendium / electronic lab notebook pattern**:
  `Git + uv capsule + nbclient/Jupyter + capsule_digest + retained ipynb + Sphinx-Needs`.
- Новый tracker появится только если возникнут десятки/сотни параметрических runs и реальная необходимость сравнения/search по metadata.
- RO-Crate оставлен как возможный будущий **export/archive format**, не runtime dependency.

## Low-noise EXP provenance

Из стандартного Jupyter execution metadata добавлен collapsed **Run details**:

- capture time;
- total/step duration;
- Python/kernel;
- freshness.

Нормальное состояние скрыто. **Stale** выводится заметным warning.

Никакой новой metadata-схемы в retained notebook и нового UI framework не добавлено.
Low-noise EXP provenance был выпущен через DocOps и применён в `llm-router`.

## Новый большой этап: Closed-loop Product Assurance

Пользователь одобрил идею сквозного Product Assurance / Product Guarantees graph и попросил перенять лучшие практики StrictDoc, OpenFastTrace и NASA, но **не подключать второй requirements engine**.

Приняты основные правила:

- authoritative graph остаётся **Sphinx-Needs**;
- путь должен быть двунаправленным:
  `GOAL → FEATURE → REQ/TREQ → IMPL → TEST`, рядом ADR/EXP;
- `required_evidence` — минимально необходимые доказательства, а не whitelist;
- revision freshness обязателен;
- вводятся **shallow coverage** для REQ/TREQ и рекурсивный **deep coverage** для FEATURE/GOAL;
- `Supported` означает, что весь нормативный subtree реализован и имеет требуемое актуальное evidence, а не «есть несколько зелёных тестов»;
- semantic coverage и code coverage — разные слои;
- source trace строится через **sphinx-codelinks**, runtime test→code trace — через **coverage.py contexts**, без собственных parser/coverage engine;
- runtime correlation сначала diagnostic, не hard gate;
- нужны явные defect reasons: missing/outdated/orphan/failing evidence, runtime trace gap, unowned code, transitive defect;
- PM-facing **Product Assurance** должен быть тихим: зелёное компактно, внимание только gaps;
- существующие views сохраняют разные роли: Product Assurance, Verification Matrix, Traceability, Living Specs, Allure, EXP;
- нужен impact analysis и позже semantic release delta;
- перед hard gates обязателен adversarial fixture suite, намеренно ломающий каждую связь;
- rollout только в `llm-router`; templates и другие consumers до завершения пилота не трогать.

## Definition of Done

Из любого GOAL должно быть возможно пройти до конкретной реализации, актуального evidence и реально исполненного source; из случайной production function или test — обратно до REQ/FEATURE/GOAL. Любой необоснованный разрыв должен быть видимым или останавливать CI.
