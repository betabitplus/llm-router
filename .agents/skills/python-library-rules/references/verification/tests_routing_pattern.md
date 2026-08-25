---
name: tests-routing-pattern
description: Reusable test-tree routing patterns for Python projects. Use when you need consistent placement rules for unit, integration, property-based, optional end-to-end, and specification-support code.
---

# Tests Routing

## Overview

Treat test depth and specification role as independent axes.

- `unit/`, `integration/`, and optional `e2e/` describe how much of the technical stack executes.
- Living Specifications describe human-readable behavioral contracts. Their source belongs under `features/`, with pytest-bdd bindings under `tests/<project>/bdd/`.

Do not use `e2e/` as a synonym for behavioral documentation.

## Tree Pattern

- `tests/<project>/unit/` — focused seams.
- `tests/<project>/integration/` — collaboration and controlled local boundaries.
- `tests/<project>/property_based/public_contract/` — generated public invariants.
- `tests/<project>/property_based/internal/` — generated private invariants.
- `tests/<project>/bdd/` — Python bindings and replay artifacts behind executable specifications.
- `tests/<project>/support/` — project-specific shared builders, assertions, fixtures, and media helpers.
- `tests/<project>/e2e/` — optional broad-stack/deployed-system checks only when that depth adds value.

## Routing Rules

- Keep human-readable behavior in `features/`; do not duplicate it in handwritten E2E prose.
- Use `Scenario Outline`/Examples when variants matter to the human contract instead of hiding meaningful cases in Python parametrization.
- Keep exhaustive technical matrices in unit/integration/property-based tests rather than multiplying Gherkin scenarios.
- Reuse `py_lib_testkit` for generic replay/evidence helpers and `tests/<project>/support/` for product-specific support.
- Keep BDD bindings thin: execution, assertions, and typed evidence only. Do not create a local scenario framework or runner.
- Technical E2E files are ordinary pytest files; they do not require a special direct-run file shape or `# %%` policy.
- Tests that intentionally verify private implementation seams may import private modules. Public-contract specifications and public-boundary tests should exercise supported public APIs.
