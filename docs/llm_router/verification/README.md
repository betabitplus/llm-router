---
name: verification
doc_type: index
description: Index of the verification-oriented docs for llm_router. Use when you need to find either the replay-backed e2e proof story or the live workbench validation story.
---

# Verification

## Overview

These docs describe the main verification layers around `llm_router`:
property-based testing, replay-backed e2e proof, and live workbench
validation.

## Files

- [public-boundary-and-errors.md](public-boundary-and-errors.md)
  Describes the checks that protect the installed public output and error boundary.
  Use it when changing response normalization or public exception translation.
- [property-based-testing.md](property-based-testing.md)
  Explains invariant-driven checks over generated public inputs and stable
  public rules.
  Use it to understand which public guarantees should hold across many input
  combinations.
- [e2e/README.md](e2e/README.md)
  Indexes the replay-backed proof docs for the concept-aligned public behavior
  guarantees.
  Use it to find proof-oriented scenarios for one public behavior slice at a
  time.
- [workbench.md](workbench.md)
  Explains the live provider probes used for executable validation and provider
  comparison.
  Use it to understand when to run real integrations to inspect behavior that
  replayed tests cannot fully answer.
