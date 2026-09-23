# 021 — Traceability Reader, Health Map и проект Verification Assurance

**Период:** 2026-09-10 → 2026-09-11
**Источник:** `Восстановление контекста Sphinx Needs -- 6aa33498-f770-83ed-a42b-4fe22f438807.md`

## Эталон UX и новая модель чтения

Пользователь попросил найти реально сильный requirements portal. Главным референсом выбран **StrictDoc**, не для копирования дизайна, а из-за трёх понятных путей:

- Feature/Capability Map — понять продукт;
- Traceability / Deep Traceability — пройти от high-level intent к деталям;
- Tree Map / coverage — увидеть сломанную ветку целиком.

Ключевой принцип: **один engineering graph → несколько специализированных views**, а не один универсальный dashboard.

## Traceability Reader

Первый canvas/SVG-прототип был отвергнут: читать гигантскую карту с pan/zoom неудобно.

После разбора StrictDoc принят другой подход:

- обычный длинный HTML document flow;
- technical IDs не должны быть главным содержимым;
- основной вопрос: **Why this exists → What must be true → What proves it now**;
- Goal и Capability показываются **один раз**, а не повторяются рядом с каждым REQ;
- структура — numbered staircase:
  `1 Goal → 1.1 Capability → 1.1.1 Requirement → 1.1.1.a Engineering rule`;
- proof/evidence ветвится от requirement;
- machine IDs/revision/concrete tests скрыты в details;
- sidebar содержит только Goals/Capabilities для быстрых прыжков.

Пользователь отдельно потребовал не превращать Reader в большую таблицу: путь должен визуально ощущаться как **последовательный поток со связями и уровнями**.

## Health / Specification Map

Health отделён от Reader.

Вместо перекрашенного dependency graph использована интерактивная **treemap**:

- весь specification hierarchy помещается в один экран;
- размер блока показывает размер ветки;
- цвет — реальный recursive health;
- hover показывает human-readable detail;
- click ведёт к canonical contract;
- implementation/tests влияют на health, но не засоряют overview.

То есть:

- Reader = спокойно прочитать причинно-смысловой путь;
- Health Map = одним взглядом увидеть состояние всего продукта.

## Verification narratives

Следом обогащены не только BDD, но и Unit / Integration / Property verification pages.

Цель — отвечать не «какой pytest node прошёл», а:

- что именно проверялось;
- какой production code реально участвовал;
- что было настоящим, а что substitute/fake/replay;
- где фактическая verification boundary;
- что наблюдалось;
- чего этот test **не доказывает**.

Не показывать фиктивные блоки: если у evidence нет media или другого материала, его не придумывать.

## Новый слой: Assurance Case / Layered Proof

Пользователь сформулировал следующий вопрос:

> если unit/integration заканчивается на fake или local server, где доказана оставшаяся часть реальности и почему самой test infrastructure можно доверять?

После исследования Assurance Case / GSN / SACM / NASA IV&V / DO-330 / ISO 26262 принято направление:

### Verification Assurance Map

Не строить ложную лестницу `Unit → Integration → BDD → E2E`.

**Тип теста и глубина proof — разные оси.**

Главная шкала должна отражать реальный verification boundary, например:

`Focused logic → Component → Integration boundary → Transport/SDK/filesystem → Public workflow/system → Live external reality`.

Unit/Property/Integration/BDD/E2E/EXP/manual — только виды evidence на этой шкале.

### Layered Proof

Для конкретного REQ/TREQ:

`Claim → verification concerns → evidence → boundary → remaining gap`.

Плюс второй уровень:

`Evidence → evidence producer → trust basis → calibration evidence`.

Это и есть обязательная **evidence-of-evidence structure**.

## Evidence producers и доверие

Отдельно нужно моделировать producers/verifiers:

- ScriptedHTTPServer;
- Fake SDK clients;
- VCR;
- JUnit→Needs importer;
- revision resolver;
- BDD binding capture;
- Allure collector;
- EXP capture pipeline и т. п.

Для каждого важно не `trusted=yes`, а **почему ему можно доверять**:

- own tests;
- golden/fixture cross-check;
- independent implementation;
- real-provider contract comparison;
- VCR/retained traffic;
- EXP/live/manual calibration;
- mature upstream tooling.

Для high-impact producer требуется более сильный trust basis.

Не использовать псевдоточные confidence percentages. Состояния должны быть качественными и объяснимыми: supported / complemented / substituted / calibrated / gap / residual doubt.

## Ключевая ownership-коррекция

В конце пользователь поймал важную архитектурную ошибку: «pilot-only» не означает, что reusable infrastructure можно держать внутри `llm-router`.

Новое постоянное правило:

> **Пилот проверяется на llm-router, но generic implementation сразу живёт в правильном Ternforge owner и сразу проходит template acceptance. Заморожен rollout других consumers, а не shared infrastructure.**

Правильный вертикальный путь каждого generic slice:

`py-testkit / DocOps / policy / infra-ci → template-components → template-py-library generated acceptance → llm-router pilot`.

Также:

- runtime truth должен захватываться **py-testkit во время pytest execution**, а не угадываться DocOps через AST;
- AST допустим только как presentation fallback;
- generic `ScriptedHTTPServer` должен жить в py-testkit, consumer оставляет только provider-specific payload/config;
- template acceptance должен проверять **реальный generated default**, без скрытых CLI-only flags.

## Точка остановки

Assurance block был разбит на 9 этапов. На основном implementation path были завершены первые два и почти завершён третий: JUnit + Allure + **coverage.py per-test contexts** связаны по pytest nodeid, BDD и non-BDD используют общий `VerificationBoundary` / runtime facts model.

**Specification Map намеренно заморожен** до завершения assurance/evidence-of-evidence блока. Коммиты/релизы этого нового блока ещё не выполнялись.
