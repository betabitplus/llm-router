---
name: request-lifecycle
doc_type: architecture
description: High-level lifecycle of one logical request in llm_router. Use when you need the end-to-end flow from caller input to normalized result.
---

# Request Lifecycle

## Overview

This document describes the lifecycle of one logical request from caller
input to normalized result.

Question this diagram answers: How does one logical request move from caller
input to normalized result and optional continuity persistence?

```mermaid
sequenceDiagram
    participant Caller
    participant Router as LLMRouter
    participant Route as Route Plan
    participant Result as Response Boundary
    participant Session
    Caller->>Router: Submit request
    Router->>Router: Resolve effective defaults
    Router->>Route: Select eligible route
    Route->>Router: Execute request
    Router->>Router: Normalize result
    Router->>Session: Persist turn if attached
    Router->>Result: Return normalized result
    Result->>Caller: Deliver result
```

## Main Flow

1. The caller enters through `LLMRouter` with content plus any explicit
   per-call requirements.
2. The system resolves the effective defaults described in
   [../concepts/settings-overrides-and-propagation.md](../concepts/settings-overrides-and-propagation.md)
   and the effective route plan.
3. The router chooses the next eligible route under the active routing policy.
4. The selected provider path executes the request using the provider wrapping
   strategy that matches the requested capabilities.
5. Structured output, the tool loop, and same-provider repair or retry,
   when required, stay inside the same logical request lifecycle.
6. The final result is normalized into `LLMRouterResponse`, following the
   terminal public boundary described in
   [../concepts/public-output-and-errors.md](../concepts/public-output-and-errors.md).
7. If a `Session` is attached, after the final result is normalized, the
   completed turn is persisted back into continuity state.

## Rules

- One caller request may imply multiple attempts, but it should remain one
  coherent logical request lifecycle.
- Route selection, structured workflows, and continuity updates happen
  inside the same logical request boundary.
