---
name: public-boundary-e2e
doc_type: verification
description: E2E proof for the real llm-router public config lifecycle through supported top-level imports.
---

# Public Boundary E2E

## Overview

This slice proves that the existing immutable `LLMRouterConfig` snapshot can be
read, installed, and read back through the supported top-level package API.

## Proof

[test_public_config_pipeline.py](../../../../tests/llm_router/e2e/public_boundary/test_public_config_pipeline.py)
runs the lifecycle through `llm_router` without private imports.

It fails if facade exports, config installation, cache invalidation, or public
snapshot identity drift away from the supported caller contract.
