---
name: property-based-testing
doc_type: verification
description: High-level role of property-based testing in llm_router. Use when you need the invariant-driven verification layer for public models, sessions, and deterministic public rules.
---

# Property-Based Testing

## Overview

This document describes the property-based testing layer in `llm_router`.
Property-based tests protect broad public invariants by generating many valid
inputs and checking that stable rules still hold.

Question this diagram answers: Where does property-based testing fit between
unit, integration, replay-backed e2e, and live workbench validation?

```mermaid
flowchart LR
    Unit["Unit Tests"] --> Property["Property-Based Tests"]
    Property --> Integration["Integration Tests"]
    Integration --> E2E["Replay-Backed E2E"]
    E2E --> Workbench["Live Workbench"]
```

## Testing Role

Property-based testing strengthens the fast verification layers by checking
that public rules hold across many generated inputs rather than a few hand-made
examples.

In `llm_router`, this layer is most useful where the public API exposes stable
models, layered defaults, and continuity semantics that should remain true
even as the private runtime evolves.

This layer stays separate from replay-backed e2e. Use
`tests/llm_router/property_based/public_contract/` for property tests that
protect only the supported package surface, and reserve
`tests/llm_router/property_based/internal/` for future private-core
invariants. It should stay faster and more local than replay-backed e2e while
still increasing confidence in public semantics.

## Target Areas

## 1. Area: Public Runtime Helpers

This area should protect omission semantics, wrapper stability, and other
generated public-shape invariants that are wider than a few named examples.

### Good Targets

- `RouterConfig.as_kwargs()`
- `RouterPolicy.as_kwargs()`
- `ProviderLimits.min_interval_seconds()`
- public schema wrappers such as `FileSchema`, `VideoSchema`, and
  `VideoUrlSchema`

These checks protect omission semantics, explicit-value preservation, copied
mapping behavior, simple validation rules, runtime config install/get
semantics, image validation boundaries, and normalized result wrapper
stability.

## 2. Area: Session Invariants

This area should protect continuity behavior that should remain true across
many generated histories and persistence shapes.

### Good Targets

- `Session.remember()`
- `Session.build_messages()`
- `Session.clear()`
- `Session.fork()`
- `Session.save()` and `Session.load()`

These checks protect continuity semantics, replay-safe persistence, and public
history meaning without relying on provider execution. This includes transcript
ordering, multimodal label placement, branch independence, metadata isolation,
and save/load round-trip behavior for persisted media-backed sessions.

## 3. Area: Future Hermetic Router Properties

This area should cover future hermetic `LLMRouter` scenarios with local
scripted providers while staying inside the public package boundary.

### Good Targets

- omitted versus explicit per-call override values
- route-default versus router-default precedence
- session growth after successful requests
- normalized result shape invariants

This should stay hermetic and still import only from the public package
boundary.

## Rules

- import the library only through the supported top-level `llm_router` package
- public-contract property tests must not import `_internal` modules
- prefer generated valid inputs over random invalid noise
- generated cases should preserve failure readability through good shrinking
- use property tests for invariant-heavy public semantics, not for provider
  transport behavior
- when one property file clearly protects one architecture concept slice,
  mirror that concept in the filename under
  `tests/llm_router/property_based/public_contract/`
- keep one property focused on one stable truth
