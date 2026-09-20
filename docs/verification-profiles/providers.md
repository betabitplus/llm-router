# Verification profiles · Provider portability

These profiles own verification design for {need}`GOAL_PROVIDER_PORTABILITY`.
Product semantics remain in the normative Requirements and Technical requirements;
targets are selected from provider-family, transport, capability, and failure
partitions rather than from whichever tests already exist.

(verification-profile-req-provider-adapter-interoperability)=

## Profile · REQ_PROVIDER_ADAPTER_INTEROPERABILITY

**Verification intent.** Prove that every supported provider family can execute one
normalized successful request across its actual adapter boundary, while provider-specific
transport details remain owned by first-class Technical requirements.

**Models:** {ref}`Provider adapter boundaries <test-plan-provider-adapter-model>`

### Required coverage

| Test level            | Boundary   | Representation | M&S target |          Target |
| --------------------- | ---------- | -------------- | ---------- | --------------: |
| Component Integration | Substitute | Surrogate      | L0         | **1 criterion** |

**Coverage basis.** The supported-adapter denominator is five families. One successful
normalized boundary path is required for OpenAI-compatible, QwenChat, AI Studio, Gemini
WebAPI, and Google GenAI. Deeper transport/media/error partitions remain owned by the
corresponding Technical requirements.

**Representation basis.** Each path executes the actual llm-router adapter against a
scripted HTTP participant or qualified in-process SDK substitute. External participants
therefore remain Surrogate at L0.

### Verification criteria

| Criterion                                     | Contract                                               | Test level            | Boundary   | Required paths | Required path IDs                                                                 | Success criterion                                                                                                                   |
| --------------------------------------------- | ------------------------------------------------------ | --------------------- | ---------- | -------------: | --------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| `VC_PROVIDER_ADAPTER_INTEROPERABILITY_MATRIX` | {need}`[[id]] <REQ_PROVIDER_ADAPTER_INTEROPERABILITY>` | Component Integration | Substitute |              5 | `OpenAI-compatible` · `QwenChat` · `AI Studio` · `Gemini WebAPI` · `Google GenAI` | One successful normalized request crosses each supported provider adapter boundary without leaking provider-specific result shapes. |

### Evidence aggregation

| Signal                 | Rule | Applies to                                                         |
| ---------------------- | ---- | ------------------------------------------------------------------ |
| Semantic coverage      | ALL  | required verification criteria and each criterion's declared paths |
| Representation         | ALL  | retained evidence for satisfied criteria                           |
| Provenance             | ALL  | retained evidence for satisfied criteria                           |
| Producer qualification | ALL  | retained evidence for satisfied criteria; every required producer  |
| Freshness              | ALL  | retained evidence for satisfied criteria                           |
| M&S validation         | ALL  | applicable surrogate/model evidence                                |

### Required technical support

| Technical requirement                                                          | Target |
| ------------------------------------------------------------------------------ | ------ |
| {need}`OpenAI-compatible transport boundary <TREQ_OPENAI_ADAPTER_BOUNDARY>`    | PASS   |
| {need}`QwenChat transport boundary <TREQ_QWENCHAT_ADAPTER_BOUNDARY>`           | PASS   |
| {need}`AI Studio transport boundary <TREQ_AISTUDIO_ADAPTER_BOUNDARY>`          | PASS   |
| {need}`Gemini WebAPI transport boundary <TREQ_GEMINI_WEBAPI_ADAPTER_BOUNDARY>` | PASS   |
| {need}`Google GenAI transport boundary <TREQ_GOOGLE_GENAI_ADAPTER_BOUNDARY>`   | PASS   |

### Fault applicability

| REQUIRED                                                                     | OPTIONAL | N/A                                                                                                                                                                                |
| ---------------------------------------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `interface.payload-schema` · `spec.wrong-outcome` · `spec.missing-partition` | —        | `impl.comparison` · `impl.boundary` · `impl.control-flow` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.error-status` |
| —                                                                            | —        | `interface.unexpected-interaction` · `architecture.forbidden-edge` · `architecture.layer-bypass` · `spec.wrong-ordering-boundary`                                                  |

#### Fault-group rationale

| Group                 | Why                                                                                                                                   |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| Implementation        | Provider-specific control flow belongs to the child Technical requirements; this parent owns the normalized interoperability outcome. |
| Runtime / dependency  | Dependency-failure behavior is owned by the adapter Technical requirements and the public provider-error Requirement.                 |
| Interface / protocol  | A successful provider payload still has to normalize into the common adapter result shape.                                            |
| Architecture          | The parent contract does not prescribe internal module topology.                                                                      |
| Specification / model | Omitting a supported provider family or returning a different normalized outcome violates the portability claim.                      |

No blocking mutation threshold is selected; required deterministic fault classes remain
blocking.

(verification-profile-treq-openai-adapter-boundary)=

## Profile · TREQ_OPENAI_ADAPTER_BOUNDARY

**Verification intent.** Prove the complete OpenAI-compatible HTTP translation boundary,
including synchronous/asynchronous success, tool results, retryable status, malformed
success payload, and remote disconnect.

**Models:** {ref}`Provider adapter boundaries <test-plan-provider-adapter-model>`

### Required coverage

| Test level            | Boundary   | Representation | M&S target |          Target |
| --------------------- | ---------- | -------------- | ---------- | --------------: |
| Component Integration | Substitute | Surrogate      | L0         | **1 criterion** |

**Coverage basis.** All six protocol partitions named by the Technical requirement are
independent obligations.

**Representation basis.** Actual adapter and HTTP-client code execute against the
scripted HTTP provider boundary; the external participant is Surrogate at L0.

### Verification criteria

| Criterion                             | Contract                                      | Test level            | Boundary   | Required paths | Required path IDs                                                                                       | Success criterion                                                                                       |
| ------------------------------------- | --------------------------------------------- | --------------------- | ---------- | -------------: | ------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `VC_PROVIDER_OPENAI_ADAPTER_BOUNDARY` | {need}`[[id]] <TREQ_OPENAI_ADAPTER_BOUNDARY>` | Component Integration | Substitute |              6 | `sync-success` · `async-success` · `tool-result` · `retryable-status` · `malformed-json` · `disconnect` | Every declared OpenAI-compatible transport/failure partition preserves the normalized adapter boundary. |

### Evidence aggregation

| Signal                 | Rule | Applies to                                                         |
| ---------------------- | ---- | ------------------------------------------------------------------ |
| Semantic coverage      | ALL  | required verification criteria and each criterion's declared paths |
| Representation         | ALL  | retained evidence for satisfied criteria                           |
| Provenance             | ALL  | retained evidence for satisfied criteria                           |
| Producer qualification | ALL  | retained evidence for satisfied criteria; every required producer  |
| Freshness              | ALL  | retained evidence for satisfied criteria                           |
| M&S validation         | ALL  | applicable surrogate/model evidence                                |

### Fault applicability

| REQUIRED                                                                                                                                      | OPTIONAL | N/A                                                                                                                           |
| --------------------------------------------------------------------------------------------------------------------------------------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `impl.control-flow` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.error-status` · `interface.payload-schema` | —        | `impl.comparison` · `impl.boundary` · `runtime.latency-timeout` · `architecture.forbidden-edge` · `architecture.layer-bypass` |
| `spec.wrong-outcome` · `spec.missing-partition`                                                                                               | —        | `interface.unexpected-interaction` · `spec.wrong-ordering-boundary`                                                           |

#### Fault-group rationale

| Group                 | Why                                                                                              |
| --------------------- | ------------------------------------------------------------------------------------------------ |
| Implementation        | Sync/async/tool/error dispatch branches implement the declared adapter boundary.                 |
| Runtime / dependency  | Disconnect and malformed successful responses are distinct dependency failure shapes.            |
| Interface / protocol  | Provider status and payload shape are direct protocol obligations.                               |
| Architecture          | No internal module edge is normative.                                                            |
| Specification / model | Every named OpenAI-compatible partition must exist and preserve the intended normalized outcome. |

No blocking mutation threshold is selected.

(verification-profile-treq-qwenchat-adapter-boundary)=

## Profile · TREQ_QWENCHAT_ADAPTER_BOUNDARY

**Verification intent.** Prove QwenChat proxy text, media upload, error translation,
tool-output normalization, and upload-retry-before-chat ordering.

**Models:** {ref}`Provider adapter boundaries <test-plan-provider-adapter-model>`

### Required coverage

| Test level            | Boundary   | Representation | M&S target |          Target |
| --------------------- | ---------- | -------------- | ---------- | --------------: |
| Component Integration | Substitute | Surrogate      | L0         | **1 criterion** |
| System Integration    | Substitute | Surrogate      | L0         | **1 criterion** |

**Coverage basis.** Four adapter-boundary partitions plus one public-runtime upload retry
ordering obligation are independently required.

**Representation basis.** Actual QwenChat adapter/runtime code executes against scripted
proxy and upload HTTP endpoints; the external participant is Surrogate at L0.

### Verification criteria

| Criterion                               | Contract                                        | Test level            | Boundary   | Required paths | Required path IDs                                                         | Success criterion                                                                                                |
| --------------------------------------- | ----------------------------------------------- | --------------------- | ---------- | -------------: | ------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `VC_PROVIDER_QWENCHAT_ADAPTER_BOUNDARY` | {need}`[[id]] <TREQ_QWENCHAT_ADAPTER_BOUNDARY>` | Component Integration | Substitute |              4 | `proxy-text` · `media-upload` · `retryable-status` · `tool-normalization` | Proxy text, media upload, provider-error translation, and tool-output normalization preserve QwenChat semantics. |
| `VC_PROVIDER_QWENCHAT_UPLOAD_RETRY`     | {need}`[[id]] <TREQ_QWENCHAT_ADAPTER_BOUNDARY>` | System Integration    | Substitute |              1 | —                                                                         | A retryable upload is retried before exactly one dependent chat request uses the successful uploaded reference.  |

### Evidence aggregation

| Signal                 | Rule | Applies to                                                         |
| ---------------------- | ---- | ------------------------------------------------------------------ |
| Semantic coverage      | ALL  | required verification criteria and each criterion's declared paths |
| Representation         | ALL  | retained evidence for satisfied criteria                           |
| Provenance             | ALL  | retained evidence for satisfied criteria                           |
| Producer qualification | ALL  | retained evidence for satisfied criteria; every required producer  |
| Freshness              | ALL  | retained evidence for satisfied criteria                           |
| M&S validation         | ALL  | applicable surrogate/model evidence                                |

### Fault applicability

| REQUIRED                                                                                                                                            | OPTIONAL | N/A                                                                                            |
| --------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------- |
| `impl.control-flow` · `runtime.unavailable-disconnect` · `interface.error-status` · `interface.payload-schema` · `interface.unexpected-interaction` | —        | `impl.comparison` · `impl.boundary` · `runtime.latency-timeout` · `runtime.malformed-response` |
| `spec.wrong-outcome` · `spec.missing-partition` · `spec.wrong-ordering-boundary`                                                                    | —        | `architecture.forbidden-edge` · `architecture.layer-bypass`                                    |

#### Fault-group rationale

| Group                 | Why                                                                                             |
| --------------------- | ----------------------------------------------------------------------------------------------- |
| Implementation        | Proxy/upload/tool routing branches implement the technical contract.                            |
| Runtime / dependency  | Upload/proxy transport loss is a relevant dependency failure.                                   |
| Interface / protocol  | Status, payload shape, and an unexpected chat/upload interaction directly violate the boundary. |
| Architecture          | Internal module topology is not normative.                                                      |
| Specification / model | All partitions and upload-before-chat ordering are required semantics.                          |

No blocking mutation threshold is selected.

(verification-profile-treq-aistudio-adapter-boundary)=

## Profile · TREQ_AISTUDIO_ADAPTER_BOUNDARY

**Verification intent.** Prove AI Studio shared text transport, native media transport,
and retryable native failure translation.

**Models:** {ref}`Provider adapter boundaries <test-plan-provider-adapter-model>`

### Required coverage

| Test level            | Boundary   | Representation | M&S target |          Target |
| --------------------- | ---------- | -------------- | ---------- | --------------: |
| Component Integration | Substitute | Surrogate      | L0         | **1 criterion** |

**Coverage basis.** Shared-text transport, native-video transport, and native retryable
failure are distinct partitions.

**Representation basis.** Actual AI Studio adapter code executes against scripted shared
and native HTTP endpoints; the external participant is Surrogate at L0.

### Verification criteria

| Criterion                               | Contract                                        | Test level            | Boundary   | Required paths | Required path IDs                                                              | Success criterion                                                                                                       |
| --------------------------------------- | ----------------------------------------------- | --------------------- | ---------- | -------------: | ------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------- |
| `VC_PROVIDER_AISTUDIO_ADAPTER_BOUNDARY` | {need}`[[id]] <TREQ_AISTUDIO_ADAPTER_BOUNDARY>` | Component Integration | Substitute |              3 | `shared-text-transport` · `native-video-transport` · `native-retryable-status` | Text uses the shared transport, native video uses native transport, and retryable native failure becomes ProviderError. |

### Evidence aggregation

| Signal                 | Rule | Applies to                                                         |
| ---------------------- | ---- | ------------------------------------------------------------------ |
| Semantic coverage      | ALL  | required verification criteria and each criterion's declared paths |
| Representation         | ALL  | retained evidence for satisfied criteria                           |
| Provenance             | ALL  | retained evidence for satisfied criteria                           |
| Producer qualification | ALL  | retained evidence for satisfied criteria; every required producer  |
| Freshness              | ALL  | retained evidence for satisfied criteria                           |
| M&S validation         | ALL  | applicable surrogate/model evidence                                |

### Fault applicability

| REQUIRED                                                                                                                              | OPTIONAL | N/A                                                                                                                               |
| ------------------------------------------------------------------------------------------------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `impl.control-flow` · `interface.unexpected-interaction` · `interface.error-status` · `spec.wrong-outcome` · `spec.missing-partition` | —        | `impl.comparison` · `impl.boundary` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` |
| —                                                                                                                                     | —        | `interface.payload-schema` · `architecture.forbidden-edge` · `architecture.layer-bypass` · `spec.wrong-ordering-boundary`         |

#### Fault-group rationale

| Group                 | Why                                                                                             |
| --------------------- | ----------------------------------------------------------------------------------------------- |
| Implementation        | Transport-selection control flow is the central technical rule.                                 |
| Runtime / dependency  | Generic dependency-loss handling belongs to resilience; native status translation remains here. |
| Interface / protocol  | Wrong endpoint selection or native error translation violates the adapter boundary.             |
| Architecture          | No particular internal layering is required.                                                    |
| Specification / model | Text/native/error partitions must all exist and produce the specified transport behavior.       |

No blocking mutation threshold is selected.

(verification-profile-treq-gemini-webapi-adapter-boundary)=

## Profile · TREQ_GEMINI_WEBAPI_ADAPTER_BOUNDARY

**Verification intent.** Prove Gemini WebAPI sync/async media behavior, tool/result
normalization, retryable status translation, and provider-specific error-code handling.

**Models:** {ref}`Provider adapter boundaries <test-plan-provider-adapter-model>`

### Required coverage

| Test level            | Boundary   | Representation | M&S target |          Target |
| --------------------- | ---------- | -------------- | ---------- | --------------: |
| Component Integration | Substitute | Surrogate      | L0         | **1 criterion** |

**Coverage basis.** Five SDK-surface partitions named by the Technical requirement are
independent obligations.

**Representation basis.** Actual adapter code executes against the qualified Gemini
WebAPI SDK substitute; the external participant remains Surrogate at L0.

### Verification criteria

| Criterion                                    | Contract                                             | Test level            | Boundary   | Required paths | Required path IDs                                                                                | Success criterion                                                                                                        |
| -------------------------------------------- | ---------------------------------------------------- | --------------------- | ---------- | -------------: | ------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------ |
| `VC_PROVIDER_GEMINI_WEBAPI_ADAPTER_BOUNDARY` | {need}`[[id]] <TREQ_GEMINI_WEBAPI_ADAPTER_BOUNDARY>` | Component Integration | Substitute |              5 | `sync-media` · `async-media` · `tool-normalization` · `retryable-status` · `provider-error-code` | Sync/async media, tool/result normalization, retryable status, and provider error-code partitions preserve the boundary. |

### Evidence aggregation

| Signal                 | Rule | Applies to                                                         |
| ---------------------- | ---- | ------------------------------------------------------------------ |
| Semantic coverage      | ALL  | required verification criteria and each criterion's declared paths |
| Representation         | ALL  | retained evidence for satisfied criteria                           |
| Provenance             | ALL  | retained evidence for satisfied criteria                           |
| Producer qualification | ALL  | retained evidence for satisfied criteria; every required producer  |
| Freshness              | ALL  | retained evidence for satisfied criteria                           |
| M&S validation         | ALL  | applicable surrogate/model evidence                                |

### Fault applicability

| REQUIRED                                                                                                                      | OPTIONAL | N/A                                                                                                                               |
| ----------------------------------------------------------------------------------------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `impl.control-flow` · `interface.error-status` · `interface.payload-schema` · `spec.wrong-outcome` · `spec.missing-partition` | —        | `impl.comparison` · `impl.boundary` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` |
| —                                                                                                                             | —        | `interface.unexpected-interaction` · `architecture.forbidden-edge` · `architecture.layer-bypass` · `spec.wrong-ordering-boundary` |

#### Fault-group rationale

| Group                 | Why                                                                                                  |
| --------------------- | ---------------------------------------------------------------------------------------------------- |
| Implementation        | Sync/async/media/tool/error branches implement the declared SDK boundary.                            |
| Runtime / dependency  | Generic dependency loss is outside this adapter-shape claim.                                         |
| Interface / protocol  | Provider-specific status/error and normalized payload shape are direct interface obligations.        |
| Architecture          | Internal module topology is not normative.                                                           |
| Specification / model | Omitting any declared SDK partition or producing the wrong normalized outcome violates the contract. |

No blocking mutation threshold is selected.

(verification-profile-treq-google-genai-adapter-boundary)=

## Profile · TREQ_GOOGLE_GENAI_ADAPTER_BOUNDARY

**Verification intent.** Prove Google GenAI synchronous success, asynchronous success,
and retryable SDK failure translation.

**Models:** {ref}`Provider adapter boundaries <test-plan-provider-adapter-model>`

### Required coverage

| Test level            | Boundary   | Representation | M&S target |          Target |
| --------------------- | ---------- | -------------- | ---------- | --------------: |
| Component Integration | Substitute | Surrogate      | L0         | **1 criterion** |

**Coverage basis.** Sync success, async success, and retryable SDK failure are independent
provider-SDK partitions.

**Representation basis.** Actual adapter code executes against the qualified Google
GenAI SDK substitute; the external participant remains Surrogate at L0.

### Verification criteria

| Criterion                                   | Contract                                            | Test level            | Boundary   | Required paths | Required path IDs                                         | Success criterion                                                                           |
| ------------------------------------------- | --------------------------------------------------- | --------------------- | ---------- | -------------: | --------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| `VC_PROVIDER_GOOGLE_GENAI_ADAPTER_BOUNDARY` | {need}`[[id]] <TREQ_GOOGLE_GENAI_ADAPTER_BOUNDARY>` | Component Integration | Substitute |              3 | `sync-success` · `async-success` · `retryable-sdk-status` | Sync/async success and retryable SDK failure preserve the normalized Google GenAI boundary. |

### Evidence aggregation

| Signal                 | Rule | Applies to                                                         |
| ---------------------- | ---- | ------------------------------------------------------------------ |
| Semantic coverage      | ALL  | required verification criteria and each criterion's declared paths |
| Representation         | ALL  | retained evidence for satisfied criteria                           |
| Provenance             | ALL  | retained evidence for satisfied criteria                           |
| Producer qualification | ALL  | retained evidence for satisfied criteria; every required producer  |
| Freshness              | ALL  | retained evidence for satisfied criteria                           |
| M&S validation         | ALL  | applicable surrogate/model evidence                                |

### Fault applicability

| REQUIRED                                                                                         | OPTIONAL | N/A                                                                                                                                                            |
| ------------------------------------------------------------------------------------------------ | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `impl.control-flow` · `interface.error-status` · `spec.wrong-outcome` · `spec.missing-partition` | —        | `impl.comparison` · `impl.boundary` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response`                              |
| —                                                                                                | —        | `interface.unexpected-interaction` · `interface.payload-schema` · `architecture.forbidden-edge` · `architecture.layer-bypass` · `spec.wrong-ordering-boundary` |

#### Fault-group rationale

| Group                 | Why                                                                                          |
| --------------------- | -------------------------------------------------------------------------------------------- |
| Implementation        | Sync/async SDK dispatch and exception translation are direct technical branches.             |
| Runtime / dependency  | Generic transport loss is outside this selected SDK-boundary partition set.                  |
| Interface / protocol  | SDK status translation is the direct interface obligation.                                   |
| Architecture          | Internal layering is not normative.                                                          |
| Specification / model | Sync, async, and retryable-failure partitions must all be represented with correct outcomes. |

No blocking mutation threshold is selected.

(verification-profile-req-async-provider-execution)=

## Profile · REQ_ASYNC_PROVIDER_EXECUTION

**Verification intent.** Prove the public async entry point across every supported
provider family for each capability partition that the Requirement promises: text,
structured output, image, document, local video, and remote video.

**Models:** {ref}`Asynchronous provider execution <test-plan-async-provider-model>`

### Required coverage

| Test level         | Boundary | Representation | M&S target |         Target |
| ------------------ | -------- | -------------- | ---------- | -------------: |
| System Integration | Replay   | Surrogate      | L0         | **6 criteria** |

**Coverage basis.** Text, structured output, and image require five provider families;
document and local video require four; remote video requires three. The independent
denominators are 5/5/5/4/4/3.

**Representation basis.** Each path executes the actual public async router and provider
adapter against retained provider interactions. Replay remains Surrogate/L0.

### Verification criteria

| Criterion                               | Contract                                      | Test level         | Boundary | Required paths | Required path IDs                                                                 | Success criterion                                                                          |
| --------------------------------------- | --------------------------------------------- | ------------------ | -------- | -------------: | --------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| `VC_ASYNC_TEXT_PROVIDER_MATRIX`         | {need}`[[id]] <REQ_ASYNC_PROVIDER_EXECUTION>` | System Integration | Replay   |              5 | `OpenAI-compatible` · `QwenChat` · `AI Studio` · `Gemini WebAPI` · `Google GenAI` | Every supported adapter family returns the normalized text contract asynchronously.        |
| `VC_ASYNC_STRUCTURED_PROVIDER_MATRIX`   | {need}`[[id]] <REQ_ASYNC_PROVIDER_EXECUTION>` | System Integration | Replay   |              5 | `OpenAI-compatible` · `QwenChat` · `AI Studio` · `Gemini WebAPI` · `Google GenAI` | Every JSON-schema-capable family returns schema-valid structured data asynchronously.      |
| `VC_ASYNC_IMAGE_PROVIDER_MATRIX`        | {need}`[[id]] <REQ_ASYNC_PROVIDER_EXECUTION>` | System Integration | Replay   |              5 | `OpenAI-compatible` · `QwenChat` · `AI Studio` · `Gemini WebAPI` · `Google GenAI` | Every image-capable family preserves grounded structured image semantics asynchronously.   |
| `VC_ASYNC_DOCUMENT_PROVIDER_MATRIX`     | {need}`[[id]] <REQ_ASYNC_PROVIDER_EXECUTION>` | System Integration | Replay   |              4 | `QwenChat` · `AI Studio` · `Gemini WebAPI` · `Google GenAI`                       | Every file-capable family preserves grounded structured document semantics asynchronously. |
| `VC_ASYNC_VIDEO_LOCAL_PROVIDER_MATRIX`  | {need}`[[id]] <REQ_ASYNC_PROVIDER_EXECUTION>` | System Integration | Replay   |              4 | `QwenChat` · `AI Studio` · `Gemini WebAPI` · `Google GenAI`                       | Every video-capable family preserves local-video semantics asynchronously.                 |
| `VC_ASYNC_VIDEO_REMOTE_PROVIDER_MATRIX` | {need}`[[id]] <REQ_ASYNC_PROVIDER_EXECUTION>` | System Integration | Replay   |              3 | `AI Studio` · `Gemini WebAPI` · `Google GenAI`                                    | Every remote-video-capable family preserves remote-video semantics asynchronously.         |

### Evidence aggregation

| Signal                 | Rule | Applies to                                                         |
| ---------------------- | ---- | ------------------------------------------------------------------ |
| Semantic coverage      | ALL  | required verification criteria and each criterion's declared paths |
| Representation         | ALL  | retained evidence for satisfied criteria                           |
| Provenance             | ALL  | retained evidence for satisfied criteria                           |
| Producer qualification | ALL  | retained evidence for satisfied criteria; every required producer  |
| Freshness              | ALL  | retained evidence for satisfied criteria                           |
| M&S validation         | ALL  | applicable surrogate/model evidence                                |

### Fault applicability

| REQUIRED                                                                                           | OPTIONAL                            | N/A                                                                                                                                                                                                                                                        |
| -------------------------------------------------------------------------------------------------- | ----------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `impl.control-flow` · `interface.payload-schema` · `spec.wrong-outcome` · `spec.missing-partition` | `impl.comparison` · `impl.boundary` | `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.unexpected-interaction` · `interface.error-status` · `architecture.forbidden-edge` · `architecture.layer-bypass` · `spec.wrong-ordering-boundary` |

#### Fault-group rationale

| Group                 | Why                                                                                                           |
| --------------------- | ------------------------------------------------------------------------------------------------------------- |
| Implementation        | Async dispatch/await control flow must preserve the result.                                                   |
| Runtime / dependency  | Retry/availability behavior belongs to resilience/routing rather than this successful async-capability claim. |
| Interface / protocol  | Provider response shape must normalize correctly.                                                             |
| Architecture          | No particular async implementation layering is normative.                                                     |
| Specification / model | Wrong public result or omission of a provider/capability partition violates the Requirement.                  |

No blocking mutation threshold is selected.

(verification-profile-req-response-normalization)=

## Profile · REQ_RESPONSE_NORMALIZATION

**Verification intent.** Compare semantically equivalent successful replies from
independently shaped provider families at the public router boundary. Provider-specific
usage parsing is delegated to the first-class usage-normalization Technical requirement.

**Models:** {ref}`Provider response normalization <test-plan-response-normalization-model>`

### Required coverage

| Test level         | Boundary   | Representation | M&S target |          Target |
| ------------------ | ---------- | -------------- | ---------- | --------------: |
| System Integration | Substitute | Surrogate      | L0         | **1 criterion** |

**Coverage basis.** OpenAI-compatible is the baseline. One independent comparison is
required for every other supported family: QwenChat, AI Studio, Gemini WebAPI, and
Google GenAI. The denominator remains four even when fewer comparisons currently exist.

**Representation basis.** Public equivalence executes actual router/adapters against
scripted provider boundaries or qualified SDK substitutes; external participants remain
Surrogate at L0.

### Verification criteria

| Criterion                          | Contract                                    | Test level         | Boundary   | Required paths | Required path IDs                                           | Success criterion                                                                                                                                 |
| ---------------------------------- | ------------------------------------------- | ------------------ | ---------- | -------------: | ----------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `VC_PROVIDER_RESPONSE_EQUIVALENCE` | {need}`[[id]] <REQ_RESPONSE_NORMALIZATION>` | System Integration | Substitute |              4 | `QwenChat` · `AI Studio` · `Gemini WebAPI` · `Google GenAI` | Each non-baseline family exposes public text/usage/tool semantics equivalent to the OpenAI-compatible baseline without provider-specific leakage. |

### Evidence aggregation

| Signal                 | Rule | Applies to                                                         |
| ---------------------- | ---- | ------------------------------------------------------------------ |
| Semantic coverage      | ALL  | required verification criteria and each criterion's declared paths |
| Representation         | ALL  | retained evidence for satisfied criteria                           |
| Provenance             | ALL  | retained evidence for satisfied criteria                           |
| Producer qualification | ALL  | retained evidence for satisfied criteria; every required producer  |
| Freshness              | ALL  | retained evidence for satisfied criteria                           |
| M&S validation         | ALL  | applicable surrogate/model evidence                                |

### Required technical support

| Technical requirement                                           | Target |
| --------------------------------------------------------------- | ------ |
| {need}`Provider usage normalization <TREQ_USAGE_NORMALIZATION>` | PASS   |

### Fault applicability

| REQUIRED                                                                     | OPTIONAL | N/A                                                                                                                                                                                          |
| ---------------------------------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `interface.payload-schema` · `spec.wrong-outcome` · `spec.missing-partition` | —        | `impl.comparison` · `impl.boundary` · `impl.control-flow` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.unexpected-interaction` |
| —                                                                            | —        | `interface.error-status` · `architecture.forbidden-edge` · `architecture.layer-bypass` · `spec.wrong-ordering-boundary`                                                                      |

#### Fault-group rationale

| Group                 | Why                                                                                                |
| --------------------- | -------------------------------------------------------------------------------------------------- |
| Implementation        | Usage-shape parsing is delegated to TREQ_USAGE_NORMALIZATION; this parent owns public equivalence. |
| Runtime / dependency  | This contract compares successful replies; provider failures are a sibling Requirement.            |
| Interface / protocol  | Provider payload shape must produce the same public response semantics.                            |
| Architecture          | No internal normalization topology is prescribed.                                                  |
| Specification / model | A wrong normalized result or a missing supported provider comparison violates portability.         |

No blocking mutation threshold is selected.

(verification-profile-treq-usage-normalization)=

## Profile · TREQ_USAGE_NORMALIZATION

**Verification intent.** Prove provider-specific usage mappings and objects normalize
into one stable UsageStats model with a consistent total token count.

**Models:** {ref}`Provider response normalization <test-plan-response-normalization-model>`

### Required coverage

| Test level | Boundary | Representation | M&S target |          Target |
| ---------- | -------- | -------------- | ---------- | --------------: |
| Component  | Local    | Actual         | —          | **1 criterion** |

**Coverage basis.** OpenAI mapping, Google object, and nested mapping are independent
input-shape partitions.

**Representation basis.** Tests execute the actual local usage normalizer directly; no
external participant or model substitute is involved.

### Verification criteria

| Criterion                         | Contract                                  | Test level | Boundary | Required paths | Required path IDs                                     | Success criterion                                                                                       |
| --------------------------------- | ----------------------------------------- | ---------- | -------- | -------------: | ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `VC_PROVIDER_USAGE_NORMALIZATION` | {need}`[[id]] <TREQ_USAGE_NORMALIZATION>` | Component  | Local    |              3 | `openai-mapping` · `google-object` · `nested-mapping` | Every supported usage shape produces the stable common usage model with a consistent total token count. |

### Evidence aggregation

| Signal                 | Rule | Applies to                                                         |
| ---------------------- | ---- | ------------------------------------------------------------------ |
| Semantic coverage      | ALL  | required verification criteria and each criterion's declared paths |
| Representation         | ALL  | retained evidence for satisfied criteria                           |
| Provenance             | ALL  | retained evidence for satisfied criteria                           |
| Producer qualification | ALL  | retained evidence for satisfied criteria; every required producer  |
| Freshness              | ALL  | retained evidence for satisfied criteria                           |
| M&S validation         | ALL  | applicable surrogate/model evidence                                |

### Fault applicability

| REQUIRED                                                                                           | OPTIONAL | N/A                                                                                                                                                          |
| -------------------------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `impl.control-flow` · `interface.payload-schema` · `spec.wrong-outcome` · `spec.missing-partition` | —        | `impl.comparison` · `impl.boundary` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.error-status` |
| —                                                                                                  | —        | `interface.unexpected-interaction` · `architecture.forbidden-edge` · `architecture.layer-bypass` · `spec.wrong-ordering-boundary`                            |

#### Fault-group rationale

| Group                 | Why                                                                               |
| --------------------- | --------------------------------------------------------------------------------- |
| Implementation        | Shape-selection branches directly implement usage normalization.                  |
| Runtime / dependency  | Normalization is local and does not depend on external runtime behavior.          |
| Interface / protocol  | Provider-specific usage payload shape is the input contract.                      |
| Architecture          | Internal module topology is not normative.                                        |
| Specification / model | Every declared usage-shape partition must normalize to the correct stable values. |

No blocking mutation threshold is selected.

(verification-profile-req-provider-error-boundary)=

## Profile · REQ_PROVIDER_ERROR_BOUNDARY

**Verification intent.** Prove that both HTTP-client and SDK-originated provider
failures cross the public router boundary only as stable ProviderError, without
exposing provider-specific exception/detail shapes.

**Models:** {ref}`Public provider-error boundary <test-plan-provider-error-boundary-model>`

### Required coverage

| Test level         | Boundary   | Representation | M&S target |         Target |
| ------------------ | ---------- | -------------- | ---------- | -------------: |
| System Integration | Substitute | Surrogate      | L0         | **2 criteria** |

**Coverage basis.** One OpenAI-compatible HTTP failure and one Google GenAI SDK-originated
failure are independently required, each observed through the public router.

**Representation basis.** Both paths execute actual llm-router/provider integration. The
HTTP path uses the scripted provider directly; the SDK path uses the actual Google GenAI
SDK redirected to the scripted provider. External behavior remains Surrogate/L0.

### Verification criteria

| Criterion                | Contract                                     | Test level         | Boundary   | Required paths | Success criterion                                                                                                     |
| ------------------------ | -------------------------------------------- | ------------------ | ---------- | -------------: | --------------------------------------------------------------------------------------------------------------------- |
| `VC_PROVIDER_ERROR_HTTP` | {need}`[[id]] <REQ_PROVIDER_ERROR_BOUNDARY>` | System Integration | Substitute |              1 | An HTTP rejection becomes ProviderError with stable status metadata, hides provider detail, and performs one request. |
| `VC_PROVIDER_ERROR_SDK`  | {need}`[[id]] <REQ_PROVIDER_ERROR_BOUNDARY>` | System Integration | Substitute |              1 | A Google GenAI SDK-originated failure becomes the same public ProviderError category with one provider request.       |

### Evidence aggregation

| Signal                 | Rule | Applies to                                                         |
| ---------------------- | ---- | ------------------------------------------------------------------ |
| Semantic coverage      | ALL  | required verification criteria and each criterion's declared paths |
| Representation         | ALL  | retained evidence for satisfied criteria                           |
| Provenance             | ALL  | retained evidence for satisfied criteria                           |
| Producer qualification | ALL  | retained evidence for satisfied criteria; every required producer  |
| Freshness              | ALL  | retained evidence for satisfied criteria                           |
| M&S validation         | ALL  | applicable surrogate/model evidence                                |

### Fault applicability

| REQUIRED                                                                                                                                                        | OPTIONAL | N/A                                                                                                                                                                                                                                 |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `impl.control-flow` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `interface.error-status` · `spec.wrong-outcome` · `spec.missing-partition` | —        | `impl.comparison` · `impl.boundary` · `runtime.malformed-response` · `interface.unexpected-interaction` · `interface.payload-schema` · `architecture.forbidden-edge` · `architecture.layer-bypass` · `spec.wrong-ordering-boundary` |

#### Fault-group rationale

| Group                 | Why                                                                                                    |
| --------------------- | ------------------------------------------------------------------------------------------------------ |
| Implementation        | Exception-translation control flow must converge on ProviderError.                                     |
| Runtime / dependency  | Timeout and disconnect are provider failures that must not leak dependency-specific exception types.   |
| Interface / protocol  | Error status is the direct interface stimulus.                                                         |
| Architecture          | The public error type is normative, not a particular internal module edge.                             |
| Specification / model | Both HTTP and SDK transport families must be represented and produce the same public failure category. |

No blocking mutation threshold is selected; required deterministic fault classes remain
blocking.
