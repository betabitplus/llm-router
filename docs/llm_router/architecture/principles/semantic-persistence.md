---
name: semantic-persistence
doc_type: architecture
description: Durable semantic-persistence guidance for llm_router internals. Use when reviewing or refactoring the continuity boundary and session behavior.
---

# Semantic Persistence

## Overview

This document defines how continuity in `llm_router` should preserve
conversation meaning and reusable media state, not provider transcript
mechanics or routing policy.

## Rules

- Persist the library's conversation model rather than provider-native request
  and response artifacts.
- Keep save, load, resume, and branch behavior provider-agnostic.
- Let continuity influence request context, not route choice or provider
  policy.
- Preserve enough semantic state that a session can survive provider changes
  and internal rewrites.

Red flag: restoring continuity requires provider-native transcript logic or
changes routing behavior for reasons unrelated to request intent.
