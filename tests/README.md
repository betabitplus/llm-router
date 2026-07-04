# Tests Layout

The `tests/` tree is split into two support layers.

## Reusable Support

`tests/support/` contains reusable testing infrastructure that is not tied to
the product package domain. This is the copy-paste layer for other Python
projects.

Typical contents:

- direct-run setup
- VCR/replay helpers
- console/rendering helpers for manual demos
- shared repo/test-data path helpers
- generic pytest-process setup

Reusable support may read repository metadata from `[tool.py_lib_starter]`, but
it should not import the product package or assume its public APIs. Product
runtime resets and provider-specific fixtures belong under the package test tree.

## Project-Specific Support

`tests/llm_router/support/` contains helpers that are specific to the
`llm_router` package and its e2e scenarios.

Typical contents:

- assertions that depend on `llm_router` response shapes
- builders that depend on `llm_router` test fixtures
- provider-specific runtime checks
- scenario-specific prompt and validation helpers
- product runtime helpers such as LLMRouter config/cache resets

## Pytest Configuration

Root `tests/conftest.py` is intentionally reusable and should stay free of
product-package imports. Product-wide fixtures live in
`tests/<package>/conftest.py` so future repos can copy the root test setup
without inheriting product behavior.

## Unit And Integration Tests

`tests/llm_router/unit/` and `tests/llm_router/integration/` may import either
the supported top-level package or `_internal` when the file is intentionally
verifying private-core behavior.

Use direct `_internal` imports in these layers only when they make the checked
private seam clearer. Keep public-contract tests and shared support on the
supported top-level package boundary.

## Property-Based Tests

`tests/llm_router/property_based/` is a separate verification layer for fast,
generated public invariants. It stays separate from `e2e/` because these files
protect deterministic public rules rather than end-to-end scenarios.

Use `public_contract/` for property tests that import only the supported
top-level package and protect public semantics. Use `internal/` for property
tests that intentionally target private implementation invariants and may
import `_internal` directly.

Inside `public_contract/`, mirror the architecture concept slices in the
filenames when one file cleanly protects one concept.

## E2E Scripts

`tests/llm_router/e2e/` is organized by testing group so the filesystem mirrors
the architecture concept slices. Each group folder contains the scenario
scripts for one concept-aligned testing area such as provider wrapping,
settings propagation, route fallback, session state, provider recovery, or
public output boundaries.

Hermetic scenarios are not all implemented the same way:

- some replay committed VCR cassettes
- some are fully local and use scripted servers or worker helpers
- each scenario file also keeps a direct-run `main()` path for manual demos

Each group folder may also contain:

- one local `cassettes/` folder when that group uses replay-backed tests

E2e scripts should import shared support and project-specific support directly.
Do not keep project-wide helper logic in the e2e folders.
