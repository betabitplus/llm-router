---
name: internal-solid
doc_type: architecture
description: Practical SOLID rules for llm_router internals. Use when reviewing or refactoring private design boundaries.
---

# Internal SOLID

## Overview

This document defines what SOLID means for the private `llm_router` design.
It is a refactor guide for the internal boundaries that must support one
logical request spanning config resolution, routing, capability handling,
provider execution, and continuity.

## Single Responsibility

- Request coordination owns lifecycle decisions: effective intent, attempt
  progression, and normalized result assembly.
- Routing state owns mutable operational policy: ordering, waiting, cooldowns,
  retries, and key choice.
- Provider integration owns remote protocol translation for one provider family.
- Continuity owns semantic continuity state and reusable media state.
- Logging, failure translation, and schema or tool normalization should be
  shared once, not reimplemented inside feature paths.

Red flag: one change forces edits in routing policy, provider translation, and
continuity logic at the same time.

## Open/Closed

- Add providers behind the same provider-independent attempt and result
  contract.
- Add capability support by extending capability bridges or adapters, not by
  spreading provider checks through orchestration.
- Add routing variants by extending policy behavior, not by growing one large
  coordinator branch tree.

Red flag: one new provider or capability requires touching many unrelated
decision paths.

## Liskov Substitution

- Any provider integration must preserve the meaning of model choice, tool
  use, structured output, multimodal input, and normalized failures.
- Different providers may execute differently, but higher layers should still
  see the same attempt and result semantics.
- When native support is missing, emulate the behavior or reject it through
  stable library semantics.

Red flag: orchestration needs provider-specific correctness patches.

## Interface Segregation

- Coordination should depend on a small execution port.
- Capability handling should depend on small tool, schema, and message-shaping
  contracts.
- Continuity, logging, and errors should expose narrow operations with one
  concern each.
- Shared sync and async decision logic should stay separate from transport
  details.

Red flag: a boundary receives a rich client or state object but uses only a
tiny subset of it.

## Dependency Inversion

- High-level policy depends on normalized attempt and result models, not SDK
  payload types.
- Execution consumes a validated snapshot, not mutable ambient config.
- Provider adapters translate outward to remote protocols and should not pull
  routing or continuity policy inward.
- External SDK details stay at the edge.

Red flag: route choice, fallback, or continuity logic needs provider-native
payload knowledge.
