# Structured output and media requirements

```{goal} Preserve rich input and structured-output semantics across providers
:id: GOAL_RICH_INPUT_OUTPUT

Callers should be able to combine structured output with text and supported media inputs through one normalized router contract.
```

```{feature} Structured and multimodal requests
:id: FEAT_STRUCTURED_OUTPUT
:derives: GOAL_RICH_INPUT_OUTPUT

The router normalizes schema and content before provider-specific execution.
```

```{req} Structured text output
:id: REQ_STRUCTURED_TEXT_OUTPUT
:status: accepted
:revision: 1
:required_evidence: impl;bdd
:derives: FEAT_STRUCTURED_OUTPUT

**Statement.** A supported text route shall be able to return deterministic structured data that validates against the caller-requested schema.

**Rationale.** Callers need structured output to be governed by their schema rather than by provider-specific response formatting.

**Verification intent.** Execute representative structured-text requests through the public router and validate the returned data against the requested schema across supported providers.
```

```{req} Document input
:id: REQ_DOCUMENT_INPUT
:status: accepted
:revision: 1
:required_evidence: impl;bdd
:derives: FEAT_STRUCTURED_OUTPUT

**Statement.** Provider routes that declare document input support shall accept a supported document input and return structured output grounded in the document contents.

**Rationale.** Document-capable callers need the same normalized structured-output contract without embedding provider-specific upload or extraction logic.

**Verification intent.** Submit a representative known document through supported public provider routes, assert grounded structured facts from its contents, and retain the input/result evidence with the execution.
```

```{req} Image input
:id: REQ_IMAGE_INPUT
:status: accepted
:revision: 1
:required_evidence: impl;bdd
:derives: FEAT_STRUCTURED_OUTPUT

**Statement.** Provider routes that declare image input support shall accept a supported image input and return structured output grounded in visible image content.

**Rationale.** Image-capable callers need one multimodal contract whose semantics do not change with the selected provider.

**Verification intent.** Submit a representative known image through supported public provider routes, assert structured facts that are visibly grounded in the image, and retain both the input image and structured result as execution evidence.
```

```{req} Video input
:id: REQ_VIDEO_INPUT
:status: accepted
:revision: 1
:required_evidence: impl;bdd
:derives: FEAT_STRUCTURED_OUTPUT

**Statement.** Provider routes that declare video input support shall accept supported local and remote video inputs and return structured output grounded in video content.

**Rationale.** Video-capable callers should not need separate public contracts for local and remote media or provider-specific result interpretation.

**Verification intent.** Execute representative supported local and remote video inputs through public provider routes, verify grounded structured facts, and retain useful media/result evidence with each execution.
```

```{req} Structured schemas normalize predictably
:id: REQ_STRUCTURED_SCHEMA_CONTRACT
:status: accepted
:revision: 1
:required_evidence: impl;unit
:derives: FEAT_STRUCTURED_OUTPUT

**Statement.** Mapping and Pydantic schema inputs shall normalize into a provider-independent schema contract that preserves required fields and common constraints and can reconstruct the requested model from valid JSON output.

**Rationale.** Schema normalization is the internal compatibility boundary that prevents provider adapters from interpreting caller schemas differently.

**Verification intent.** Directly verify representative mapping and Pydantic schemas, required/common constraints, and model reconstruction from valid normalized JSON output.
```

```{req} Multimodal content normalization preserves intent
:id: REQ_MULTIMODAL_CONTENT_NORMALIZATION
:status: accepted
:revision: 1
:required_evidence: impl;unit
:derives: FEAT_STRUCTURED_OUTPUT

**Statement.** Content normalization shall preserve the ordering of text and supported media parts, reject unsupported content promptly, and revalidate raw media modes before provider execution.

**Rationale.** Provider adapters can only preserve multimodal request meaning if the normalized content model keeps ordering and media-mode invariants intact.

**Verification intent.** Directly verify ordered mixed content, supported raw media modes, and rejection of unsupported or invalid content before provider execution.
```
