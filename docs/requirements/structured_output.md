# Structured output and media requirements

{doc}`← Intent map <index>` · {doc}`Whole-system map <maps>` · {doc}`Release health <../specification-health>`

Read this page as one continuous branch of the product idea. Start with the local
**Idea branch** for the big picture. Then inspect only the contracts you care about;
under each Requirement/Technical requirement, **Follow this contract to proof** reveals one downstream hop so
you can drill into implementation or executed verification without opening a global
catalogue.

```{goal} Preserve rich input and structured-output semantics across providers
:id: GOAL_RICH_INPUT_OUTPUT
:collapse: true

Callers should be able to combine structured output with text and supported media inputs through one normalized router contract.
```

## Idea branch

This is the whole local intent hierarchy. Use the graph to see the forest; use the
clickable next-level links below it to enter the branch you want.

::::{only} graphviz_available

```{needflow} Rich input and output idea branch
:engine: graphviz
:direction: down
:root_id: GOAL_RICH_INPUT_OUTPUT
:root_direction: incoming
:root_depth: 3
:filter: type in ["goal", "feature", "req", "treq"]
:link_types: derives
:alt: Rich input and output from goal through requirements and technical requirements
```

::::

::::{only} not graphviz_available
The graph renderer is unavailable in this build. The authoritative Goal, Capability,
Requirement, and Technical requirement cards below preserve the same hierarchy through their relationship
links.
::::

### Enter this branch

```{needlist}
:filter: "'GOAL_RICH_INPUT_OUTPUT' in derives"
```

## See this branch as executable behavior

When you want to verify the public behavior at this abstraction level before opening
individual test evidence, use the Living Specifications for this branch. They keep
Gherkin, current execution status, attachments, and the exact requirement provenance
together.

- {ref}`Structured-output executable behavior <living-specs-area-structured-output>`

```{feature} Structured and multimodal requests
:id: FEAT_STRUCTURED_OUTPUT
:collapse: true
:derives: GOAL_RICH_INPUT_OUTPUT

The router normalizes schema and content before provider-specific execution.
```

Contracts in this capability:

```{needlist}
:filter: "'FEAT_STRUCTURED_OUTPUT' in derives"
```

```{req} Structured text output
:id: REQ_STRUCTURED_TEXT_OUTPUT
:collapse: true
:status: accepted
:revision: 1
:required_evidence: impl;bdd
:derives: FEAT_STRUCTURED_OUTPUT

**Statement.** A supported text route shall be able to return deterministic structured data that validates against the caller-requested schema.

**Rationale.** Callers need structured output to be governed by their schema rather than by provider-specific response formatting.

**Verification intent.** Execute representative structured-text requests through the public router and validate the returned data against the requested schema across supported providers.
```

::::{dropdown} Follow this contract to proof

```{needlist}
:filter: "'REQ_STRUCTURED_TEXT_OUTPUT' in derives or 'REQ_STRUCTURED_TEXT_OUTPUT' in implements or 'REQ_STRUCTURED_TEXT_OUTPUT' in verifies"
```

::::

```{req} Document input
:id: REQ_DOCUMENT_INPUT
:collapse: true
:status: accepted
:revision: 1
:required_evidence: impl;bdd
:derives: FEAT_STRUCTURED_OUTPUT

**Statement.** Provider routes that declare document input support shall accept a supported document input and return structured output grounded in the document contents.

**Rationale.** Document-capable callers need the same normalized structured-output contract without embedding provider-specific upload or extraction logic.

**Verification intent.** Submit a representative known document through supported public provider routes, assert grounded structured facts from its contents, and retain the input/result evidence with the execution.
```

::::{dropdown} Follow this contract to proof

```{needlist}
:filter: "'REQ_DOCUMENT_INPUT' in derives or 'REQ_DOCUMENT_INPUT' in implements or 'REQ_DOCUMENT_INPUT' in verifies"
```

::::

```{req} Image input
:id: REQ_IMAGE_INPUT
:collapse: true
:status: accepted
:revision: 1
:required_evidence: impl;bdd
:derives: FEAT_STRUCTURED_OUTPUT

**Statement.** Provider routes that declare image input support shall accept a supported image input and return structured output grounded in visible image content.

**Rationale.** Image-capable callers need one multimodal contract whose semantics do not change with the selected provider.

**Verification intent.** Submit a representative known image through supported public provider routes, assert structured facts that are visibly grounded in the image, and retain both the input image and structured result as execution evidence.
```

::::{dropdown} Follow this contract to proof

```{needlist}
:filter: "'REQ_IMAGE_INPUT' in derives or 'REQ_IMAGE_INPUT' in implements or 'REQ_IMAGE_INPUT' in verifies"
```

::::

```{req} Video input
:id: REQ_VIDEO_INPUT
:collapse: true
:status: accepted
:revision: 1
:required_evidence: impl;bdd
:derives: FEAT_STRUCTURED_OUTPUT

**Statement.** Provider routes that declare video input support shall accept supported local and remote video inputs and return structured output grounded in video content.

**Rationale.** Video-capable callers should not need separate public contracts for local and remote media or provider-specific result interpretation.

**Verification intent.** Execute representative supported local and remote video inputs through public provider routes, verify grounded structured facts, and retain useful media/result evidence with each execution.
```

::::{dropdown} Follow this contract to proof

```{needlist}
:filter: "'REQ_VIDEO_INPUT' in derives or 'REQ_VIDEO_INPUT' in implements or 'REQ_VIDEO_INPUT' in verifies"
```

::::

```{req} Structured schemas normalize predictably
:id: REQ_STRUCTURED_SCHEMA_CONTRACT
:collapse: true
:status: accepted
:revision: 1
:required_evidence: impl;unit
:derives: FEAT_STRUCTURED_OUTPUT

**Statement.** Mapping and Pydantic schema inputs shall normalize into a provider-independent schema contract that preserves required fields and common constraints and can reconstruct the requested model from valid JSON output.

**Rationale.** Schema normalization is the internal compatibility boundary that prevents provider adapters from interpreting caller schemas differently.

**Verification intent.** Directly verify representative mapping and Pydantic schemas, required/common constraints, and model reconstruction from valid normalized JSON output.
```

::::{dropdown} Follow this contract to proof

```{needlist}
:filter: "'REQ_STRUCTURED_SCHEMA_CONTRACT' in derives or 'REQ_STRUCTURED_SCHEMA_CONTRACT' in implements or 'REQ_STRUCTURED_SCHEMA_CONTRACT' in verifies"
```

::::

```{req} Multimodal content normalization preserves intent
:id: REQ_MULTIMODAL_CONTENT_NORMALIZATION
:collapse: true
:status: accepted
:revision: 1
:required_evidence: impl;unit
:derives: FEAT_STRUCTURED_OUTPUT

**Statement.** Content normalization shall preserve the ordering of text and supported media parts, reject unsupported content promptly, and revalidate raw media modes before provider execution.

**Rationale.** Provider adapters can only preserve multimodal request meaning if the normalized content model keeps ordering and media-mode invariants intact.

**Verification intent.** Directly verify ordered mixed content, supported raw media modes, and rejection of unsupported or invalid content before provider execution.
```

::::{dropdown} Follow this contract to proof

```{needlist}
:filter: "'REQ_MULTIMODAL_CONTENT_NORMALIZATION' in derives or 'REQ_MULTIMODAL_CONTENT_NORMALIZATION' in implements or 'REQ_MULTIMODAL_CONTENT_NORMALIZATION' in verifies"
```

::::

## Continue nearby

Do not jump back to an artifact catalogue when this branch raises a neighboring
question. These are the closest semantic continuations:

- {doc}`Provider portability <providers>` — how normalized content crosses provider boundaries.
- {doc}`Tool orchestration <tools>` — another normalized capability spanning providers.
- {doc}`Session continuity <sessions>` — how rich content participates in retained conversation state.

To zoom all the way out, return to the {doc}`Intent map <index>`. To investigate a release
blocker instead, open {doc}`Specification health <../specification-health>`.
