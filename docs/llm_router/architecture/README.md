---
name: architecture
doc_type: index
description: Index of the stable architecture docs for llm_router. Use when you need high-level logic, flow, and boundary docs.
---

# Architecture

## Overview

These docs describe the integrated system model behind `llm_router` and the
focused architecture slices that deepen it. They intentionally avoid current
file layout and provider-specific implementation detail.

## Files

- [system.md](system.md)
  Explains the integrated architecture story for one logical request.
  Use it to understand how the main runtime slices fit together end to end.
- [principles/README.md](principles/README.md)
  Indexes the durable internal-design principle docs.
  Use it to navigate the design rules that shape private boundaries and
  refactors.
- [principles/solid.md](principles/solid.md)
  Defines project-specific SOLID guidance for boundary ownership and extension.
  Use it to understand why extension points stay clean without mixing concerns.
- [principles/state-and-snapshots.md](principles/state-and-snapshots.md)
  Defines how validated snapshots stay stable and mutable execution state
  stays bounded.
  Use it to understand why request policy is fixed up front while runtime
  state remains controlled.
- [principles/capability-normalization.md](principles/capability-normalization.md)
  Defines how capability meaning is established before provider translation
  fans out.
  Use it to understand why tools, schemas, and media are interpreted once in
  library terms before adapter projection.
- [principles/semantic-persistence.md](principles/semantic-persistence.md)
  Defines continuity as semantic persistence, separate from routing and
  transport history.
  Use it to understand why reusable conversation meaning is preserved without
  coupling to provider transcripts.
- [principles/ports-and-adapters.md](principles/ports-and-adapters.md)
  Defines how provider and transport mechanics stay at the edge of the private
  runtime.
  Use it to understand why external protocols do not leak into core routing
  and state logic.
- [concepts/README.md](concepts/README.md)
  Indexes the primary vertical-slice concept docs.
  Use it to choose one focused runtime model slice at a time.
- [flows/README.md](flows/README.md)
  Indexes the end-to-end flow docs.
  Use it to follow the major system lifecycle from input to result.
- [flows/request-lifecycle.md](flows/request-lifecycle.md)
  Explains one logical request from caller input to normalized result and
  optional continuity persistence.
  Use it to understand why one request stays coherent across routing,
  execution, and persistence.
- [concepts/provider-sdk-wrapping.md](concepts/provider-sdk-wrapping.md)
  Explains how one public request is translated into provider-specific SDK
  workflows.
  Use it to understand why provider integrations can vary internally while the
  public request shape stays stable.
- [concepts/settings-overrides-and-propagation.md](concepts/settings-overrides-and-propagation.md)
  Explains where settings can be supplied, which layer wins, and how effective
  values reach execution.
  Use it to understand why request-time behavior follows one predictable
  precedence order.
- [concepts/route-fallback-and-attempt-policy.md](concepts/route-fallback-and-attempt-policy.md)
  Explains route choice, waits, fallback, and attempt-level routing policy.
  Use it to understand why routing can retry or switch routes without changing
  the public request contract.
- [concepts/session-state-and-isolation.md](concepts/session-state-and-isolation.md)
  Explains session attachment, persistence, branching, and isolation semantics.
  Use it to understand why continuity can be reused safely across related
  requests.
- [concepts/provider-retries-and-output-repair.md](concepts/provider-retries-and-output-repair.md)
  Explains same-provider retry and output-repair behavior after a route has
  been chosen.
  Use it to understand why recovery stays inside one provider path before
  wider fallback begins.
- [concepts/public-output-and-errors.md](concepts/public-output-and-errors.md)
  Explains the normalized output boundary and the public error surface.
  Use it to understand why callers see one stable result and error model
  across providers.
