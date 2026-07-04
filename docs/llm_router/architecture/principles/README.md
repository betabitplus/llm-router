---
name: principles
doc_type: index
description: Index of the durable internal-design principle docs for llm_router. Use when you need stable guidance for shaping or refactoring private implementation boundaries.
---

# Principles

## Overview

These docs describe durable design principles for the private `llm_router`
implementation. They focus on internal organization: which boundary owns a
concern, where mutable state may live, where provider translation begins, and
where library vocabulary must be established.

## Files

- [solid.md](solid.md)
  Defines project-specific SOLID guidance for boundary ownership and extension.
  Use it to understand why private boundaries stay extensible without mixing
  concerns.
- [state-and-snapshots.md](state-and-snapshots.md)
  Defines how validated snapshots stay stable and mutable execution state
  stays bounded.
  Use it to understand why policy is fixed up front while mutable execution
  state stays controlled.
- [capability-normalization.md](capability-normalization.md)
  Defines how capability meaning is established before provider translation
  fans out.
  Use it to understand why tools, schemas, and media are interpreted once in
  library terms before adapter projection.
- [semantic-persistence.md](semantic-persistence.md)
  Defines continuity as semantic persistence, separate from routing and
  transport history.
  Use it to understand why reusable conversation meaning is preserved without
  coupling to provider transcripts.
- [ports-and-adapters.md](ports-and-adapters.md)
  Defines how provider and transport mechanics stay at the edge of the private
  runtime.
  Use it to understand why external protocols do not leak into core routing
  and state logic.
