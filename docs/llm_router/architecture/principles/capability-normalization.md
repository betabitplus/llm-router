---
name: capability-normalization
doc_type: architecture
description: Durable capability-normalization guidance for llm_router internals. Use when reviewing or refactoring how private boundaries handle tools, schemas, media, and other provider-varying behaviors.
---

# Capability Normalization

## Overview

This document defines how `llm_router` should model capabilities in library
vocabulary first, then adapt them to providers with different native protocols
and levels of support.

## Rules

- Express tools, structured output, multimodal input, usage semantics, and
  continuity-related behaviors in provider-independent terms.
- Normalize capability intent before provider branching begins.
- Let provider integrations translate or emulate capability behavior, but not
  redefine its library meaning.
- If native support is missing, degrade through stable library semantics rather
  than exposing provider-native quirks upward.

Red flag: routing or orchestration needs provider-specific capability branches
to preserve normal behavior.
