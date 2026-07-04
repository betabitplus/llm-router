---
name: state-and-snapshots
doc_type: architecture
description: Durable state and snapshot guidance for llm_router internals. Use when reviewing or refactoring private ownership of policy and mutable execution state.
---

# State And Snapshots

## Overview

This document defines how `llm_router` should execute one logical request
against one consistent validated snapshot while keeping mutable operational
state local to the boundaries that need it.

## Rules

- Validate and resolve policy before remote work begins, then treat that
  validated snapshot as stable for the lifetime of one logical request.
- Keep mutable operational state local to routing and concurrency concerns such
  as ordering, waits, cooldowns, retries, and key rotation.
- One orchestration layer should own lifecycle flow while smaller stateful
  parts own bounded operational decisions.
- Do not let mutable ambient config become part of ordinary execution logic.

Red flag: one logical request can observe changing policy or hidden shared
mutation mid-execution.
