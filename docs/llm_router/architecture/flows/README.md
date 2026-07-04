---
name: architecture-flows
doc_type: index
description: Index of the architecture flows for llm_router. Use when you need one end-to-end system flow at a time.
---

# Flows

## Overview

These docs describe end-to-end architectural flows. They focus on how one
logical request moves through the system over time.

## Files

- [request-lifecycle.md](request-lifecycle.md)
  Explains one logical request from caller input to normalized result and
  optional continuity persistence.
  Use it to understand why one request stays coherent from input through
  execution, output, and optional persistence.
