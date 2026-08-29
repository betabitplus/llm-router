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
:revision: 1
:needs_artifacts: impl;bdd
:derives: FEAT_STRUCTURED_OUTPUT

A supported text route must be able to produce deterministic data that validates against the requested structured schema.
```

```{req} Document input
:id: REQ_DOCUMENT_INPUT
:revision: 1
:needs_artifacts: impl;bdd
:derives: FEAT_STRUCTURED_OUTPUT

Supported provider routes must accept the example document and produce grounded structured output from its contents.
```

```{req} Image input
:id: REQ_IMAGE_INPUT
:revision: 1
:needs_artifacts: impl;bdd
:derives: FEAT_STRUCTURED_OUTPUT

Supported provider routes must accept the example image and produce structured output describing its visible content.
```

```{req} Video input
:id: REQ_VIDEO_INPUT
:revision: 1
:needs_artifacts: impl;bdd
:derives: FEAT_STRUCTURED_OUTPUT

Supported provider routes must accept supported local and remote video inputs and produce structured output describing their content.
```

```{req} Structured schemas normalize predictably
:id: REQ_STRUCTURED_SCHEMA_CONTRACT
:revision: 1
:needs_artifacts: impl;unit
:derives: FEAT_STRUCTURED_OUTPUT

Mapping and Pydantic schema inputs must normalize into a provider-independent schema contract that enforces required fields, common constraints, and model reconstruction from JSON output.
```

```{req} Multimodal content normalization preserves intent
:id: REQ_MULTIMODAL_CONTENT_NORMALIZATION
:revision: 1
:needs_artifacts: impl;unit
:derives: FEAT_STRUCTURED_OUTPUT

Normalization must preserve the ordering of text and supported media parts, reject unsupported content promptly, and revalidate raw media modes before provider execution.
```
