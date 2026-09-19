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
:revision: 2
:required_evidence: impl;bdd
:derives: FEAT_STRUCTURED_OUTPUT

**Statement.** A supported text route shall return provider-independent structured data that parses and validates against the caller-requested schema. Provider-specific response formatting shall not change the public structured result.

**Rationale.** Callers need structured output to be governed by their schema rather than by provider-specific response formatting.
```

::::{dropdown} Follow this contract to proof

{ref}`Verification profile → <verification-profile-req-structured-text-output>`

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

```

::::{dropdown} Follow this contract to proof

{ref}`Verification profile → <verification-profile-req-document-input>`

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

```

::::{dropdown} Follow this contract to proof

{ref}`Verification profile → <verification-profile-req-image-input>`

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

```

::::{dropdown} Follow this contract to proof

{ref}`Verification profile → <verification-profile-req-video-input>`

```{needlist}
:filter: "'REQ_VIDEO_INPUT' in derives or 'REQ_VIDEO_INPUT' in implements or 'REQ_VIDEO_INPUT' in verifies"
```

::::

```{req} Structured schemas normalize predictably
:id: REQ_STRUCTURED_SCHEMA_CONTRACT
:collapse: true
:status: accepted
:revision: 2
:required_evidence: impl;unit
:derives: FEAT_STRUCTURED_OUTPUT

**Statement.** Mapping schema inputs shall be valid object JSON Schemas and router-side validation shall enforce their declared Draft 2020-12 semantics after provider execution. Pydantic model types shall preserve their generated schema and reconstruct the requested model from valid JSON output. Provider-specific schema transforms shall not weaken router-side validation.

**Rationale.** Schema normalization is the internal compatibility boundary that prevents provider adapters from silently weakening or interpreting caller schemas differently.
```

::::{dropdown} Follow this contract to proof

{ref}`Verification profile → <verification-profile-req-structured-schema-contract>`

```{needlist}
:filter: "'REQ_STRUCTURED_SCHEMA_CONTRACT' in derives or 'REQ_STRUCTURED_SCHEMA_CONTRACT' in implements or 'REQ_STRUCTURED_SCHEMA_CONTRACT' in verifies"
```

::::

```{req} Multimodal content normalization preserves intent
:id: REQ_MULTIMODAL_CONTENT_NORMALIZATION
:collapse: true
:status: accepted
:revision: 2
:required_evidence: impl;unit
:derives: FEAT_STRUCTURED_OUTPUT

**Statement.** Content normalization shall preserve caller order, message role and metadata, media kind, and public descriptor metadata across text, file, image, local-video, and remote-video parts. Unsupported top-level content or media parts and raw images outside supported mode or dimension bounds shall fail before provider execution.

**Rationale.** Provider adapters can only preserve multimodal request meaning if the normalized content model keeps ordering, message semantics, descriptor metadata, and media invariants intact.
```

::::{dropdown} Follow this contract to proof

{ref}`Verification profile → <verification-profile-req-multimodal-content-normalization>`

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
