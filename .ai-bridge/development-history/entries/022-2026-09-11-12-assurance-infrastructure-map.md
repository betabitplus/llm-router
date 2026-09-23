# 022 — Assurance infrastructure vertical slice и Verification Assurance Map

**Период:** 2026-09-11 → 2026-09-12
**Источник:** `Восстановление контекста Sphinx Needs -- 6aa4861b-475c-83eb-b7da-4406ce8c8b3b.md`

## Общая assurance-модель доведена через owner-слои

- Закрыт единый `VerificationBoundary` для BDD и обычных Unit/Integration/Property evidence.
- Один свежий запуск теперь даёт **JUnit + Allure + coverage.py contexts**, а DocOps связывает всё по конкретному pytest nodeid.
- Runtime facts имеют приоритет над markers/source inference; AST остаётся только fallback/presentation enrichment.
- Generic `ScriptedHTTPServer` вынесен из `llm-router` в **py-testkit** вместе с qualification tests. В consumer осталась только product-specific семантика boundary.
- Правило ownership закреплено практически:
  **test mechanics → testkit; assurance semantics → DocOps; product meaning → consumer**.
- Infra-ci только оркестрирует retained evidence bundle и передаёт его DocOps.

## Template contract стал реальным

Раньше generated-project acceptance включал traceability скрытым CLI override:

`-o ternforge_traceability=true`.

Это признано неправильным.

Теперь:

- traceability включена в реальный generated default;
- starter project получает минимальный честный GOAL → FEATURE → REQ baseline;
- starter tests получают настоящие `verifies` / `verification_kind`;
- production loci получают `@impl`;
- generated acceptance запускает одну реальную pytest-сессию и строит portal/dossier из JUnit + Allure + coverage contexts;
- никакой acceptance-only магии.

Эта инфраструктура прошла цепочку:
`py-testkit / DocOps / infra-ci → template-components → template-py-library → generated consumer → llm-router pilot`.

## Качество owner-кода

Новые assurance modules сначала оказались слишком крупными. Вместо ослабления Radon/MI thresholds код разделили по обязанностям:

- runtime evidence;
- coverage contexts;
- source analysis;
- case/boundary inference;
- narrative rendering;
- review/proof views.

JUnit ingestion переведён на `defusedxml`.

Это закрепило правило: новый assurance слой не должен превращать DocOps в очередной god-module.

## Pilot checkpoint

После propagation pilot прошёл tests/schema/portal gates, а runtime evidence уже явно различал substitute / not covered / captured boundary. Это подтвердило, что общий owner-chain работает на реальном consumer.

## Boundary Interaction / Property / E2E

В py-testkit добавлен typed `evidence.boundary_interaction(...)`, который передаёт только объективные runtime facts:

- boundary;
- interaction;
- participant;
- target;
- transport.

DocOps интерпретирует их, но не придумывает.

Добавлены специальные narratives:

- **Property**: generated domain → production subject → invariant;
- **E2E**: reach/terminal interactions; сам label E2E не означает live-provider fidelity;
- несколько boundary interactions могут существовать одновременно;
- произвольный HTTP substitute не классифицируется как ScriptedHTTPServer по имени.

Hypothesis/generated execution тоже должен подтверждаться runtime evidence, а не `verification_kind` или AST.

## Verification Assurance Map

Этап 8 начался с общего `proof_model`, чтобы Reader и Assurance Map использовали одну current-revision proof semantics.

Новая карта строит поток:

Flow: `Contract → Implementation → Verification → Runtime assurance`

и:

- не создаёт отдельный score/source of truth;
- completeness берёт из существующего specification health;
- stale/predated evidence остаётся видимым, но не закрывает proof;
- runtime details не копируются в Needs — карта ведёт к authoritative narratives;
- UI сделан stock Sphinx/docutils без нового JS/CSS.

На реальном pilot: **44/44 active REQ/TREQ complete proof**; BDD, Property и Integration links проверены браузером.

Verification Assurance Map была протянута через shared DocOps/template layers.

## Требования пользователя, закреплённые здесь

- Любой generic slice должен сразу проходить всю shared-infrastructure/template цепочку.
- Runtime truth не выводить из названия теста или структуры source.
- Не добавлять искусственный E2E obligation только ради полноты taxonomy: если в продукте сейчас 0 E2E obligations, это допустимо.
- Не понижать quality thresholds ради нового assurance-кода.
- Specification Map функционально не трогать до завершения assurance block.
- Другие consumers не раскатывать.

## Точка остановки

Verification Assurance Map уже была реализована в DocOps и проверена в браузере, но её финальная propagation через generated-project acceptance в `llm-router` ещё выполнялась. Последний assurance block ещё не начинался.
