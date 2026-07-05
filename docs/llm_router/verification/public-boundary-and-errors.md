---
name: public-boundary-and-errors-verification
doc_type: verification
description: Verification of the stable llm_router output and error boundary.
---

# Public Boundary And Errors Verification

The public boundary is protected by unit, integration, property, installed
artifact, public API, and end-to-end checks. The
[`public-output-and-errors`](e2e/public-output-and-errors.md) slice proves
response normalization, provider error translation, tool failures, and tool
round limits through the supported top-level package API.

`py-lib-check-public-contract-boundary`, import-linter contracts, and the
installed-artifact smoke tests additionally prevent private implementation
modules from becoming caller dependencies.
