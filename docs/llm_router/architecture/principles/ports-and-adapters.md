---
name: ports-and-adapters
doc_type: architecture
description: Durable ports-and-adapters guidance for llm_router internals. Use when reviewing or refactoring private design boundaries around provider execution.
---

# Ports And Adapters

## Overview

This document defines how `llm_router` should keep its core runtime model
separate from external SDKs, HTTP payloads, and provider-native request
formats.

## Rules

- Routing, fallback, capability policy, and continuity should speak in
  library concepts such as attempts, normalized result meaning, tool intent, and
  continuity state.
- Provider integrations should translate between those concepts and one
  external system.
- External client objects, transport exceptions, and provider payload shapes
  should stop at the adapter boundary.
- Adding a provider should mostly mean adding or extending an adapter, not
  teaching the coordinator new protocol rules.

Red flag: orchestration or routing logic needs to branch on provider-native
payload structure.
