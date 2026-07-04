---
name: architecture-concepts
doc_type: index
description: Index of the architecture concept slices for llm_router. Use when you need one focused runtime slice at a time.
---

# Concepts

## Overview

These docs describe the primary vertical slices of the `llm_router` runtime
model. Each file owns one stable concept slice rather than one mechanism-only
topic.

## Files

- [provider-sdk-wrapping.md](provider-sdk-wrapping.md)
  Explains how one public request is translated into provider-specific SDK
  workflows.
  Use it to understand why provider integrations can vary internally while the
  public request shape stays stable.
- [settings-overrides-and-propagation.md](settings-overrides-and-propagation.md)
  Explains where settings can be supplied, which layer wins, and how effective
  values reach execution.
  Use it to understand why request-time behavior follows one predictable
  precedence order.
- [route-fallback-and-attempt-policy.md](route-fallback-and-attempt-policy.md)
  Explains route choice, waits, fallback, and attempt-level routing policy.
  Use it to understand why routing can retry or switch routes without changing
  the public request contract.
- [session-state-and-isolation.md](session-state-and-isolation.md)
  Explains session attachment, persistence, branching, and isolation semantics.
  Use it to understand why continuity can be reused safely across related
  requests.
- [provider-retries-and-output-repair.md](provider-retries-and-output-repair.md)
  Explains same-provider retry and output-repair behavior after a route has
  been chosen.
  Use it to understand why recovery stays inside one provider path before
  wider fallback begins.
- [public-output-and-errors.md](public-output-and-errors.md)
  Explains the normalized output boundary and the public error surface.
  Use it to understand why callers see one stable result and error model
  across providers.
