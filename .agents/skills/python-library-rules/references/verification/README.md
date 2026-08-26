---
name: verification-index
description: Index of verification references for python-library-rules. Use when the task is about test placement, executable specifications, technical verification, or live workbench probes.
---

# Verification References

## Overview

Use these references to keep technical test depth, executable behavioral specifications, and manual workbench probes distinct.

## Files

- [tests_routing_pattern.md](tests_routing_pattern.md)
  Placement rules, including the separate `features/` + `tests/<project>/bdd/` Living Specifications axis.
- [workbench_script_template.md](workbench_script_template.md)
  Manual live workbench script shape.

Do not maintain a special E2E file template or mirrored E2E documentation taxonomy. Genuine E2E tests use ordinary pytest conventions; human-readable behavioral contracts use Gherkin Living Specifications.
