---
name: public-boundary-and-errors
doc_type: architecture
description: Stable output and error boundaries exposed by llm_router.
---

# Public Boundary And Errors

The public package returns provider-neutral `LLMRouterResponse` values and raises
exceptions from the `LLMRouterError` hierarchy. Provider SDK objects, transport
exceptions, raw payloads, and implementation-only state stay behind the private
implementation boundary.

The detailed product semantics are documented in
[Public Output And Errors](public-output-and-errors.md). Shared bounded preview
and structured logging primitives come directly from `py-lib-runtime`; the
package retains only its product-specific error taxonomy and event vocabulary.
