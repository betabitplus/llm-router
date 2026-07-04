# Internal Implementation

## Overview

The private runtime lives under `src/llm_router/_internal`. It is consumed only
by the public `_api` facade and is not a supported caller import surface.

## Package Map

- `config/`: immutable runtime config models, default assembly, validation, and
  process-wide installed snapshot state.
- `runtime/`: route expansion, effective settings, limiter state, request
  orchestration, timeouts, fallback, and tracing.
- `session/`: provider-neutral session history and semantic persistence.
- `capabilities/`: provider-neutral content, media, schema, tool, and usage
  normalization.
- `providers/`: provider adapter ports, registry/cache lifecycle, retry helpers,
  and concrete SDK adapters.
- `output.py`: public response DTO assembly from internal outcomes.
- `errors.py`: private exceptions and boundary translation helpers.
- `ids.py`: private request, attempt, and tool-call identifier helpers.

## Boundary

`llm_router._internal.__init__` exports only the private-root symbols consumed by
`src/llm_router/_api`: config dataclasses and config lifecycle helpers,
`RouterRuntime`, `SessionStore`, and `clear_adapter_caches`.

Public callers should keep importing from `llm_router`. Provider adapters and
deep runtime helpers stay private to `_internal` subpackages.

## Topic Docs

- `config-and-snapshots.md`: immutable config assembly and installed snapshots.
- `routing-and-limits.md`: route expansion, fallback order, limit buckets, and
  wait policy.
- `session-persistence.md`: provider-neutral history, save/load, and fork
  behavior.
- `capability-normalization.md`: content, media, schema, tools, usage, repair,
  and tool-loop normalization.
- `provider-adapters.md`: provider port and concrete adapter boundaries.
- `request-lifecycle.md`: runtime ordering from public call to session update.
- `observability-and-errors.md`: retry logs, error translation, and public
  output safety.
- `verification.md`: local commands and proof areas for unit, integration,
  property, e2e, hook, and running-loop checks.
