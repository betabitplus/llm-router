---
name: e2e-verification
doc_type: index
description: Index of the replay-backed e2e verification docs for llm_router. Use when you need the proof story for one focused e2e guarantee or workflow area.
---

# E2E Verification

## Overview

These docs describe what the replay-backed e2e suite proves at the public
boundary. Each file follows one architecture concept slice so the proof
structure stays aligned with `architecture/concepts/` and
`tests/llm_router/e2e/`.

## Files

- [provider-sdk-wrapping.md](provider-sdk-wrapping.md)
  Explains text, image, document, video, and tool loop workflows proven
  across provider families.
  Use it to understand which provider-facing workflows are covered at the
  public boundary.
- [settings-overrides-and-propagation.md](settings-overrides-and-propagation.md)
  Explains how omission, override, and explicit `None` stay distinct at the
  public request boundary.
  Use it to understand why precedence and null-handling rules remain stable in
  e2e behavior.
- [route-fallback-and-attempt-policy.md](route-fallback-and-attempt-policy.md)
  Explains route choice, waiting, and per-attempt timeout behavior.
  Use it to understand which routing decisions are proven end to end rather
  than only described architecturally.
- [session-state-and-isolation.md](session-state-and-isolation.md)
  Explains continuity, persistence, branching, and concurrent request isolation.
  Use it to understand which state-sharing and isolation guarantees are
  actually exercised at the public boundary.
- [provider-retries-and-output-repair.md](provider-retries-and-output-repair.md)
  Explains retry recovery for transient provider failures and guided repair for
  invalid structured output.
  Use it to understand which same-provider recovery behaviors are proven
  without route-level fallback.
- [public-output-and-errors.md](public-output-and-errors.md)
  Explains tool safety boundaries, public error behavior, and normalized-output parity.
  Use it to understand which output and error guarantees callers can rely on
  across providers.
