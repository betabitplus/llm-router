(verification-profiles-structured-output)=

# Verification profiles · Rich input and structured output

These profiles own verification design for {need}`GOAL_RICH_INPUT_OUTPUT`.
Normative product semantics remain in Requirements. Coverage denominators come from the
declared provider capabilities and caller-visible schema/content semantics, not from the
tests that happen to exist.

(verification-profile-req-structured-text-output)=

## Profile · REQ_STRUCTURED_TEXT_OUTPUT

**Verification intent.** Prove the public structured-text contract through every
supported adapter family that declares JSON-schema support, with the same caller schema
validated after provider-specific execution.

**Models:** {ref}`Structured output provider matrix <test-plan-structured-output-provider-matrix>`

### Required coverage

| Test level         | Boundary | Representation | M&S target |          Target |
| ------------------ | -------- | -------------- | ---------- | --------------: |
| System Integration | Replay   | Surrogate      | L0         | **1 criterion** |

**Coverage basis.** The current supported adapter-family denominator is five:
OpenAI-compatible, QwenChat, AI Studio, Gemini WebAPI, and Google GenAI. Each declares
JSON-schema support and therefore owes one retained structured-text path.

**Representation basis.** Each path executes the actual public router, schema
normalizer, runtime, and adapter against retained provider interactions. Replay remains
Surrogate/L0; stronger dependency-fidelity evidence is tracked separately rather than
inferred from a cassette.

### Verification criteria

| Criterion                            | Contract                                    | Test level         | Boundary | Required paths | Success criterion                                                                                                                                                                      |
| ------------------------------------ | ------------------------------------------- | ------------------ | -------- | -------------: | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `VC_STRUCTURED_TEXT_PROVIDER_MATRIX` | {need}`[[id]] <REQ_STRUCTURED_TEXT_OUTPUT>` | System Integration | Replay   |              5 | Every supported adapter family returns a public structured result that validates against the same caller-requested schema without provider-specific result formatting leaking through. |

### Evidence aggregation

| Signal                 | Rule | Applies to                                                         |
| ---------------------- | ---- | ------------------------------------------------------------------ |
| Semantic coverage      | ALL  | the required criterion and all five declared provider-family paths |
| Representation         | ALL  | retained evidence for satisfied paths                              |
| Provenance             | ALL  | retained evidence for satisfied paths                              |
| Producer qualification | ALL  | retained evidence for satisfied paths                              |
| Freshness              | ALL  | retained evidence for satisfied paths                              |
| M&S validation         | ALL  | applicable replay/model evidence                                   |

### Fault applicability

| REQUIRED                                                                                           | OPTIONAL        | N/A                                                                                                                                                                                                                                                                            |
| -------------------------------------------------------------------------------------------------- | --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `impl.control-flow` · `interface.payload-schema` · `spec.wrong-outcome` · `spec.missing-partition` | `impl.boundary` | `impl.comparison` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.unexpected-interaction` · `interface.error-status` · `architecture.forbidden-edge` · `architecture.layer-bypass` · `spec.wrong-ordering-boundary` |

#### Fault-group rationale

| Group                 | Why                                                                                                                                    |
| --------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| Implementation        | Schema-present/result-normalization control flow directly selects the structured path; numeric comparisons are not defining semantics. |
| Runtime / dependency  | Transport/retry failures belong to resilience/provider-error contracts; this profile is the successful structured-result claim.        |
| Interface / protocol  | A provider payload that cannot yield the requested structure directly challenges the structured boundary.                              |
| Architecture          | No particular internal module topology is normative for the public result.                                                             |
| Specification / model | A wrong structured result or an omitted supported provider family invalidates the claim.                                               |

No blocking mutation threshold is selected; required deterministic fault classes remain
blocking.

(verification-profile-req-document-input)=

## Profile · REQ_DOCUMENT_INPUT

**Verification intent.** Prove grounded structured extraction from a known document
through every adapter family that declares file and JSON-schema support.

**Models:** {ref}`Grounded multimodal provider matrix <test-plan-grounded-media-matrix>`

### Required coverage

| Test level         | Boundary | Representation | M&S target |          Target |
| ------------------ | -------- | -------------- | ---------- | --------------: |
| System Integration | Replay   | Surrogate      | L0         | **1 criterion** |

**Coverage basis.** Four adapter families declare both file and JSON-schema support:
QwenChat, AI Studio, Gemini WebAPI, and Google GenAI. OpenAI-compatible does not declare
file support and is not in this denominator.

**Representation basis.** Retained replay executes the actual public router,
normalization, and adapter translation, while the external provider remains a replayed
surrogate. Grounding is checked against deterministic facts extracted from the retained
input document.

### Verification criteria

| Criterion                              | Contract                            | Test level         | Boundary | Required paths | Success criterion                                                                                                                       |
| -------------------------------------- | ----------------------------------- | ------------------ | -------- | -------------: | --------------------------------------------------------------------------------------------------------------------------------------- |
| `VC_DOCUMENT_GROUNDED_PROVIDER_MATRIX` | {need}`[[id]] <REQ_DOCUMENT_INPUT>` | System Integration | Replay   |              4 | Every file-capable adapter family accepts the same known document and returns schema-valid facts demonstrably grounded in its contents. |

### Evidence aggregation

| Signal                 | Rule | Applies to                                                         |
| ---------------------- | ---- | ------------------------------------------------------------------ |
| Semantic coverage      | ALL  | the required criterion and all four declared provider-family paths |
| Representation         | ALL  | retained evidence for satisfied paths                              |
| Provenance             | ALL  | retained evidence for satisfied paths                              |
| Producer qualification | ALL  | retained evidence for satisfied paths                              |
| Freshness              | ALL  | retained evidence for satisfied paths                              |
| M&S validation         | ALL  | applicable replay/model evidence                                   |

### Fault applicability

| REQUIRED                                                                                           | OPTIONAL                           | N/A                                                                                                                                                                                                                                                         |
| -------------------------------------------------------------------------------------------------- | ---------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `impl.control-flow` · `interface.payload-schema` · `spec.wrong-outcome` · `spec.missing-partition` | `interface.unexpected-interaction` | `impl.comparison` · `impl.boundary` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.error-status` · `architecture.forbidden-edge` · `architecture.layer-bypass` · `spec.wrong-ordering-boundary` |

#### Fault-group rationale

| Group                 | Why                                                                                                               |
| --------------------- | ----------------------------------------------------------------------------------------------------------------- |
| Implementation        | Media-vs-text dispatch and result parsing are branch-sensitive; numeric thresholds are not the document contract. |
| Runtime / dependency  | This profile covers successful grounded extraction rather than provider availability.                             |
| Interface / protocol  | Wrong media/schema payload shape can destroy grounding; extra calls are secondary but diagnostically useful.      |
| Architecture          | No particular internal module graph is required.                                                                  |
| Specification / model | Wrong document facts or omission of a declared file-capable provider family violates the Requirement.             |

No blocking mutation threshold is selected; required deterministic fault classes remain
blocking.

(verification-profile-req-image-input)=

## Profile · REQ_IMAGE_INPUT

**Verification intent.** Prove grounded structured image understanding through every
adapter family that declares image and JSON-schema support.

**Models:** {ref}`Grounded multimodal provider matrix <test-plan-grounded-media-matrix>`

### Required coverage

| Test level         | Boundary | Representation | M&S target |          Target |
| ------------------ | -------- | -------------- | ---------- | --------------: |
| System Integration | Replay   | Surrogate      | L0         | **1 criterion** |

**Coverage basis.** Five adapter families declare image and JSON-schema support:
OpenAI-compatible, QwenChat, AI Studio, Gemini WebAPI, and Google GenAI.

**Representation basis.** Retained replay executes actual image normalization, public
runtime, and adapter translation; the external provider remains Surrogate/L0. Structured
facts are checked against visible, deterministic properties of the retained input image.

### Verification criteria

| Criterion                           | Contract                         | Test level         | Boundary | Required paths | Success criterion                                                                                                               |
| ----------------------------------- | -------------------------------- | ------------------ | -------- | -------------: | ------------------------------------------------------------------------------------------------------------------------------- |
| `VC_IMAGE_GROUNDED_PROVIDER_MATRIX` | {need}`[[id]] <REQ_IMAGE_INPUT>` | System Integration | Replay   |              5 | Every image-capable adapter family accepts the retained image and returns schema-valid facts grounded in visible image content. |

### Evidence aggregation

| Signal                 | Rule | Applies to                                                         |
| ---------------------- | ---- | ------------------------------------------------------------------ |
| Semantic coverage      | ALL  | the required criterion and all five declared provider-family paths |
| Representation         | ALL  | retained evidence for satisfied paths                              |
| Provenance             | ALL  | retained evidence for satisfied paths                              |
| Producer qualification | ALL  | retained evidence for satisfied paths                              |
| Freshness              | ALL  | retained evidence for satisfied paths                              |
| M&S validation         | ALL  | applicable replay/model evidence                                   |

### Fault applicability

| REQUIRED                                                                                           | OPTIONAL                           | N/A                                                                                                                                                                                                                                                         |
| -------------------------------------------------------------------------------------------------- | ---------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `impl.control-flow` · `interface.payload-schema` · `spec.wrong-outcome` · `spec.missing-partition` | `interface.unexpected-interaction` | `impl.comparison` · `impl.boundary` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.error-status` · `architecture.forbidden-edge` · `architecture.layer-bypass` · `spec.wrong-ordering-boundary` |

#### Fault-group rationale

| Group                 | Why                                                                                              |
| --------------------- | ------------------------------------------------------------------------------------------------ |
| Implementation        | Media translation/result parsing branches determine whether image semantics survive.             |
| Runtime / dependency  | Successful understanding is the claim; availability/retry failures are owned elsewhere.          |
| Interface / protocol  | An incorrect media/schema payload shape directly challenges image handling.                      |
| Architecture          | Internal layering is not part of the public image claim.                                         |
| Specification / model | Incorrect visible facts or an omitted image-capable provider family invalidates the Requirement. |

No blocking mutation threshold is selected; required deterministic fault classes remain
blocking.

(verification-profile-req-video-input)=

## Profile · REQ_VIDEO_INPUT

**Verification intent.** Prove both local-file and remote-URL video semantics through
every adapter family that declares video and JSON-schema support.

**Models:** {ref}`Grounded multimodal provider matrix <test-plan-grounded-media-matrix>`

### Required coverage

| Test level         | Boundary | Representation | M&S target |         Target |
| ------------------ | -------- | -------------- | ---------- | -------------: |
| System Integration | Replay   | Surrogate      | L0         | **2 criteria** |

**Coverage basis.** QwenChat, AI Studio, Gemini WebAPI, and Google GenAI all declare
video and JSON-schema support. The Requirement explicitly names local and remote inputs,
so each mode has an independent four-provider denominator: eight retained paths total.

**Representation basis.** Both modes execute actual public/runtime/adapter code against
replayed provider interactions. Replay remains Surrogate/L0 and is not promoted to live
dependency evidence.

### Verification criteria

| Criterion                         | Contract                         | Test level         | Boundary | Required paths | Success criterion                                                                                                                                       |
| --------------------------------- | -------------------------------- | ------------------ | -------- | -------------: | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `VC_VIDEO_LOCAL_GROUNDED_MATRIX`  | {need}`[[id]] <REQ_VIDEO_INPUT>` | System Integration | Replay   |              4 | Every video-capable adapter family accepts the retained local clip and returns schema-valid action/location facts grounded in it.                       |
| `VC_VIDEO_REMOTE_GROUNDED_MATRIX` | {need}`[[id]] <REQ_VIDEO_INPUT>` | System Integration | Replay   |              4 | Every video-capable adapter family accepts the retained remote URL and returns the same public structured-result contract grounded in the remote video. |

### Evidence aggregation

| Signal                 | Rule | Applies to                                          |
| ---------------------- | ---- | --------------------------------------------------- |
| Semantic coverage      | ALL  | both required criteria and all eight declared paths |
| Representation         | ALL  | retained evidence for satisfied paths               |
| Provenance             | ALL  | retained evidence for satisfied paths               |
| Producer qualification | ALL  | retained evidence for satisfied paths               |
| Freshness              | ALL  | retained evidence for satisfied paths               |
| M&S validation         | ALL  | applicable replay/model evidence                    |

### Fault applicability

| REQUIRED                                                                                           | OPTIONAL                                                            | N/A                                                                                                                                                                                                                        |
| -------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `impl.control-flow` · `interface.payload-schema` · `spec.wrong-outcome` · `spec.missing-partition` | `interface.unexpected-interaction` · `spec.wrong-ordering-boundary` | `impl.comparison` · `impl.boundary` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.error-status` · `architecture.forbidden-edge` · `architecture.layer-bypass` |

#### Fault-group rationale

| Group                 | Why                                                                                                                                                      |
| --------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Implementation        | Local-vs-remote media dispatch and provider translation are branch-sensitive.                                                                            |
| Runtime / dependency  | This profile is the successful video-understanding claim rather than availability/retry behavior.                                                        |
| Interface / protocol  | Wrong video/schema payload shape invalidates the request; unexpected extra interactions are secondary diagnostics.                                       |
| Architecture          | No internal topology is prescribed.                                                                                                                      |
| Specification / model | Both local and remote partitions plus every declared video-capable provider family are mandatory; ordering is useful but not the primary semantic claim. |

No blocking mutation threshold is selected; required deterministic fault classes remain
blocking.

(verification-profile-req-structured-schema-contract)=

## Profile · REQ_STRUCTURED_SCHEMA_CONTRACT

**Verification intent.** Prove that caller schema semantics are retained locally before
provider-specific transforms: valid mapping schemas are enforced, invalid mapping
schemas fail closed, and Pydantic outputs reconstruct the requested model.

**Models:** {ref}`Provider-independent schema validation <test-plan-schema-contract-model>`

### Required coverage

| Test level | Boundary | Representation | M&S target |         Target |
| ---------- | -------- | -------------- | ---------- | -------------: |
| Component  | Local    | Actual         | —          | **3 criteria** |

**Coverage basis.** Three independent semantics are required: Pydantic reconstruction,
mapping-schema enforcement across nested/common JSON Schema constraints, and fail-closed
rejection of an invalid caller schema before it can be sent to a provider.

**Representation basis.** These paths execute the actual local schema contract and do
not require an external dependency.

### Verification criteria

| Criterion                             | Contract                                        | Test level | Boundary | Required paths | Success criterion                                                                                                                                              |
| ------------------------------------- | ----------------------------------------------- | ---------- | -------- | -------------: | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `VC_SCHEMA_PYDANTIC_RECONSTRUCTION`   | {need}`[[id]] <REQ_STRUCTURED_SCHEMA_CONTRACT>` | Component  | Local    |              1 | A Pydantic model type retains its generated schema and valid JSON reconstructs the requested model type.                                                       |
| `VC_SCHEMA_MAPPING_ENFORCEMENT`       | {need}`[[id]] <REQ_STRUCTURED_SCHEMA_CONTRACT>` | Component  | Local    |              1 | A valid object JSON Schema mapping is preserved and router-side validation enforces its declared nested/common constraints rather than silently ignoring them. |
| `VC_SCHEMA_INVALID_MAPPING_REJECTION` | {need}`[[id]] <REQ_STRUCTURED_SCHEMA_CONTRACT>` | Component  | Local    |              1 | An invalid JSON Schema mapping is rejected during normalization before provider execution can begin.                                                           |

### Evidence aggregation

| Signal                 | Rule | Applies to                                            |
| ---------------------- | ---- | ----------------------------------------------------- |
| Semantic coverage      | ALL  | all required verification criteria and declared paths |
| Representation         | ALL  | retained evidence                                     |
| Provenance             | ALL  | retained evidence                                     |
| Producer qualification | ALL  | retained evidence                                     |
| Freshness              | ALL  | retained evidence                                     |
| M&S validation         | ALL  | applicable surrogate/model evidence                   |

### Fault applicability

| REQUIRED                                                                                                                                                               | OPTIONAL | N/A                                                                                                                                                                                                                          |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `impl.comparison` · `impl.boundary` · `impl.control-flow` · `interface.payload-schema` · `architecture.layer-bypass` · `spec.wrong-outcome` · `spec.missing-partition` | —        | `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.unexpected-interaction` · `interface.error-status` · `architecture.forbidden-edge` · `spec.wrong-ordering-boundary` |

#### Fault-group rationale

| Group                 | Why                                                                                                    |
| --------------------- | ------------------------------------------------------------------------------------------------------ |
| Implementation        | Constraint comparisons/bounds and validation branches define accept/reject behavior.                   |
| Runtime / dependency  | Schema semantics are local and dependency availability is irrelevant.                                  |
| Interface / protocol  | Caller schema/output shape is the data contract being validated.                                       |
| Architecture          | Bypassing router-side validation in favor of provider-only validation can weaken caller semantics.     |
| Specification / model | Wrong acceptance/rejection or omission of mapping/Pydantic partitions invalidates the schema contract. |

No blocking mutation threshold is selected; required deterministic fault classes remain
blocking.

(verification-profile-req-multimodal-content-normalization)=

## Profile · REQ_MULTIMODAL_CONTENT_NORMALIZATION

**Verification intent.** Prove that provider-neutral content preserves ordered caller
intent and descriptor metadata, while unsupported content and invalid raw images fail
before a provider is invoked.

**Models:** {ref}`Multimodal content normalization <test-plan-content-normalization-model>`

### Required coverage

| Test level | Boundary | Representation | M&S target |          Target |
| ---------- | -------- | -------------- | ---------- | --------------: |
| Component  | Local    | Actual         | —          |  **3 criteria** |
| System     | Local    | Actual         | —          | **1 criterion** |

**Coverage basis.** Local semantics require ordered mixed parts plus descriptor metadata,
ChatMessage role/meta preservation, and five invalid-input partitions: unsupported
top-level content, unsupported part/media type, invalid image mode, too-small image, and
too-large image. Because the Requirement says rejection occurs before provider
execution, two representative public negative paths must additionally prove zero
provider-boundary interactions.

**Representation basis.** Normalization and public rejection paths execute actual local
runtime code. The System paths are Local because the expected outcome prevents any
material provider interaction.

### Verification criteria

| Criterion                              | Contract                                              | Test level | Boundary | Required paths | Success criterion                                                                                                                |
| -------------------------------------- | ----------------------------------------------------- | ---------- | -------- | -------------: | -------------------------------------------------------------------------------------------------------------------------------- |
| `VC_CONTENT_ORDER_DESCRIPTOR_METADATA` | {need}`[[id]] <REQ_MULTIMODAL_CONTENT_NORMALIZATION>` | Component  | Local    |              1 | Mixed text/file/image/local-video/remote-video parts retain caller order and relevant descriptor metadata.                       |
| `VC_CONTENT_CHAT_MESSAGE_SEMANTICS`    | {need}`[[id]] <REQ_MULTIMODAL_CONTENT_NORMALIZATION>` | Component  | Local    |              1 | Normalizing a ChatMessage preserves role, ordered parts, and metadata values while owning a separate top-level metadata mapping. |
| `VC_CONTENT_INVALID_INPUT_REJECTION`   | {need}`[[id]] <REQ_MULTIMODAL_CONTENT_NORMALIZATION>` | Component  | Local    |              5 | Unsupported top-level/part inputs and raw images violating mode/min/max bounds are rejected locally.                             |
| `VC_CONTENT_PRE_PROVIDER_REJECTION`    | {need}`[[id]] <REQ_MULTIMODAL_CONTENT_NORMALIZATION>` | System     | Local    |              2 | Representative unsupported-content and invalid-image public requests fail with zero provider-boundary interactions.              |

### Evidence aggregation

| Signal                 | Rule | Applies to                                            |
| ---------------------- | ---- | ----------------------------------------------------- |
| Semantic coverage      | ALL  | all required verification criteria and declared paths |
| Representation         | ALL  | retained evidence                                     |
| Provenance             | ALL  | retained evidence                                     |
| Producer qualification | ALL  | retained evidence                                     |
| Freshness              | ALL  | retained evidence                                     |
| M&S validation         | ALL  | applicable surrogate/model evidence                   |

### Fault applicability

| REQUIRED                                                                                                                                                                                                        | OPTIONAL | N/A                                                                                                                                                                                 |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `impl.comparison` · `impl.boundary` · `impl.control-flow` · `interface.unexpected-interaction` · `architecture.layer-bypass` · `spec.wrong-outcome` · `spec.missing-partition` · `spec.wrong-ordering-boundary` | —        | `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.error-status` · `interface.payload-schema` · `architecture.forbidden-edge` |

#### Fault-group rationale

| Group                 | Why                                                                                                                 |
| --------------------- | ------------------------------------------------------------------------------------------------------------------- |
| Implementation        | Image bounds, branch selection, and ordered-part construction directly implement the normalized semantics.          |
| Runtime / dependency  | Invalid content must terminate locally, so dependency failures are outside this claim.                              |
| Interface / protocol  | Any provider interaction after locally invalid input is explicitly forbidden.                                       |
| Architecture          | Bypassing provider-neutral normalization before adapter execution breaks the required boundary.                     |
| Specification / model | Wrong order/metadata, missing invalid-input partitions, or reject-after-provider ordering violates the Requirement. |

No blocking mutation threshold is selected; required deterministic fault classes remain
blocking.
