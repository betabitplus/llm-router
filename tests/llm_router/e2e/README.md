# E2E Groups

The e2e suite is grouped by testing purpose so the filesystem mirrors the
architecture docs.

## Groups

- `provider_sdk_wrapping/`
- `settings_overrides_and_propagation/`
- `route_fallback_and_attempt_policy/`
- `session_state_and_isolation/`
- `provider_retries_and_output_repair/`
- `public_output_and_errors/`

These package names mirror the architecture concept slices with Python-safe
snake_case. E2E checks are ordinary pytest modules; run them through pytest rather
than a parallel module-mode execution path.

## Layout Rule

Each group folder may contain:

- the pytest modules for that testing group
- a local `cassettes/` folder when that group uses replay-backed tests

Shared helpers still belong in:

- `py_lib_testkit` for repository-agnostic support
- `tests/llm_router/support/` for product-specific support
