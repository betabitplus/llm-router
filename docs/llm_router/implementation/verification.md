# Verification

## Scope

This document describes the local verification loop for the private
`llm_router._internal` runtime. The commands prove the public facade still
works while the private runtime owns config, routing, sessions, capabilities,
provider adapters, retries, logging, and response normalization.

Run commands through `direnv exec .` when the shell has not already loaded the
repo environment.

## Unit And Integration Proofs

Unit tests prove narrow private contracts: config snapshots, route expansion,
effective settings, limiter state, session serialization, content/schema/tool
normalization, provider payload construction, retry classification, output
normalization, error translation, logging events, and adapter cache clearing.

```bash
direnv exec . rtk proxy uv run pytest tests/llm_router/unit
```

Integration tests prove private subsystems working together with fake
providers, fake servers, routing policy, retry and repair orchestration,
concurrency isolation, and logging observability.

```bash
direnv exec . rtk proxy uv run pytest tests/llm_router/integration
```

## Property Proofs

Internal property tests exercise generated config, settings, session, tool-loop,
and schema-repair inputs against stable invariants. Public-contract property
tests prove the supported caller-facing DTOs, error boundaries, settings
precedence, fallback policy, provider wrapping, and session behavior remain
unchanged.

```bash
direnv exec . rtk proxy uv run pytest tests/llm_router/property_based/internal
direnv exec . rtk proxy uv run pytest tests/llm_router/property_based/public_contract
```

## E2E Proofs

The replay-backed e2e tests prove the runtime against preserved public
scenarios: provider SDK wrapping, provider retries, structured repair, public
output and errors, route fallback and wait policy, session isolation, and
settings propagation.

```bash
direnv exec . rtk proxy uv run pytest tests/llm_router/e2e
```

Phase-local e2e checks for the observability and concurrency phase are:

```bash
direnv exec . rtk proxy uv run pytest tests/llm_router/e2e/session_state_and_isolation
direnv exec . rtk proxy uv run pytest tests/llm_router/e2e/settings_overrides_and_propagation
```

## Running-Loop Proofs

Every e2e module must also run through the nested-event-loop reproduction
script. Regenerate the module list from the filesystem before running it.

```bash
direnv exec . rtk proxy uv run python - <<'PY'
from pathlib import Path
import subprocess

for path in sorted(Path("tests/llm_router/e2e").rglob("test_*.py")):
    module = ".".join(path.with_suffix("").parts)
    subprocess.run(
        [
            "uv",
            "run",
            "python",
            "scripts/runtime/reproduce_running_loop.py",
            module,
        ],
        check=True,
    )
PY
```

## Quality Gates

The final quality loop covers lint, formatting, spelling, normal pre-commit
hooks, and pre-push hooks.

```bash
direnv exec . rtk proxy uv run ruff check .
direnv exec . rtk proxy uv run ruff format --check .
direnv exec . rtk proxy uv run typos
direnv exec . rtk proxy uv run pre-commit run --all-files
direnv exec . rtk proxy uv run pre-commit run --hook-stage pre-push --all-files
```
