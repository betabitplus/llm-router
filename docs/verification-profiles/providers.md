# Verification profiles · Provider portability

These profiles own verification design for {need}`GOAL_PROVIDER_PORTABILITY`.
Product semantics remain in the normative Requirements and Technical requirements;
targets are selected from provider-family, transport, capability, and failure
partitions rather than from whichever tests already exist.

(verification-profile-req-provider-adapter-interoperability)=

## Profile · REQ_PROVIDER_ADAPTER_INTEROPERABILITY

**Verification intent.** Prove every supported adapter family at its actual llm-router
translation boundary, including each transport, failure, and ordering partition named
by the derived Technical requirements.

**Models:** {ref}`Provider adapter boundaries <test-plan-provider-adapter-model>`

### Required coverage

| Test level            | Boundary   | Representation | M&S target |          Target |
| --------------------- | ---------- | -------------- | ---------- | --------------: |
| Component Integration | Substitute | Surrogate      | L0         |  **5 criteria** |
| System Integration    | Substitute | Surrogate      | L0         | **1 criterion** |

**Coverage basis.** OpenAI-compatible requires sync/async success, tool-result
translation, error status, malformed response, and disconnect. QwenChat requires proxy
text, media upload, error translation, tool-output normalization, plus public-runtime
upload-retry ordering. AI Studio requires both text and native-media transports plus
native failure translation. Gemini WebAPI and Google GenAI require their declared SDK
sync/async and error partitions.

**Representation basis.** HTTP paths execute actual adapters against the scripted
provider boundary. SDK paths execute actual adapters against qualified in-process SDK
substitutes. L0 is the minimum target; stronger retained M&S qualification remains
visible in Actual.

### Verification criteria

| Criterion                                    | Contract                                             | Test level            | Boundary   | Required paths | Success criterion                                                                                                            |
| -------------------------------------------- | ---------------------------------------------------- | --------------------- | ---------- | -------------: | ---------------------------------------------------------------------------------------------------------------------------- |
| `VC_PROVIDER_OPENAI_ADAPTER_BOUNDARY`        | {need}`[[id]] <TREQ_OPENAI_ADAPTER_BOUNDARY>`        | Component Integration | Substitute |              6 | Sync/async success, tool-result emission, retryable status, malformed JSON, and disconnect preserve the OpenAI boundary.     |
| `VC_PROVIDER_QWENCHAT_ADAPTER_BOUNDARY`      | {need}`[[id]] <TREQ_QWENCHAT_ADAPTER_BOUNDARY>`      | Component Integration | Substitute |              4 | Proxy text, media upload, provider-error translation, and structured/textual tool normalization preserve QwenChat semantics. |
| `VC_PROVIDER_AISTUDIO_ADAPTER_BOUNDARY`      | {need}`[[id]] <TREQ_AISTUDIO_ADAPTER_BOUNDARY>`      | Component Integration | Substitute |              3 | Text uses the shared transport, native video uses the native transport, and retryable native failure becomes ProviderError.  |
| `VC_PROVIDER_GEMINI_WEBAPI_ADAPTER_BOUNDARY` | {need}`[[id]] <TREQ_GEMINI_WEBAPI_ADAPTER_BOUNDARY>` | Component Integration | Substitute |              5 | Sync/async media, structured/tool output, retryable status, and provider-specific error-code partitions are preserved.       |
| `VC_PROVIDER_GOOGLE_GENAI_ADAPTER_BOUNDARY`  | {need}`[[id]] <TREQ_GOOGLE_GENAI_ADAPTER_BOUNDARY>`  | Component Integration | Substitute |              3 | Sync success, async success, and retryable SDK failure preserve the normalized Google GenAI boundary.                        |
| `VC_PROVIDER_QWENCHAT_UPLOAD_RETRY`          | {need}`[[id]] <TREQ_QWENCHAT_ADAPTER_BOUNDARY>`      | System Integration    | Substitute |              1 | A retryable upload is retried before exactly one subsequent chat request uses the successful uploaded reference.             |

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

| REQUIRED                                                                                                                                                                                                                                                                                          | OPTIONAL                            | N/A                                                         |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------- | ----------------------------------------------------------- |
| `impl.control-flow` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.unexpected-interaction` · `interface.error-status` · `interface.payload-schema` · `spec.wrong-outcome` · `spec.missing-partition` · `spec.wrong-ordering-boundary` | `impl.comparison` · `impl.boundary` | `architecture.forbidden-edge` · `architecture.layer-bypass` |

#### Fault-group rationale

| Group                 | Why                                                                                                                                 |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| Implementation        | Transport/shape branches are normative; comparison/boundary mutation is secondary because no numeric threshold defines portability. |
| Runtime / dependency  | Timeout, disconnect, and malformed dependency responses are distinct adapter-boundary failure shapes.                               |
| Interface / protocol  | Wrong endpoint/order/status/payload behavior directly invalidates transport translation.                                            |
| Architecture          | The Requirement constrains observable adapter semantics, not a particular internal dependency graph.                                |
| Specification / model | Every provider family and named partition must exist; Qwen upload must precede the dependent chat request.                          |

No blocking mutation threshold is selected; required deterministic fault classes remain
blocking.

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

**Coverage basis.** Capability declarations define the denominator independently of the
existing async scenarios. Text and JSON-schema execution are supported by all five
adapter families. Image is supported by all five. Document, local-video, and
remote-video execution are supported by QwenChat, AI Studio, Gemini WebAPI, and Google
GenAI, producing independent 5/5/5/4/4/4 provider-family denominators. This deliberately
exercises async-only branches such as Qwen media upload and AI Studio native-media
dispatch instead of allowing one successful async path per provider to stand in for all
declared capabilities.

**Representation basis.** Each path executes the actual public async router and
provider adapter against retained provider interactions. Replay remains Surrogate/L0;
a cassette proves the retained async integration path, not a live provider claim.

### Verification criteria

| Criterion                               | Contract                                      | Test level         | Boundary | Required paths | Success criterion                                                                                           |
| --------------------------------------- | --------------------------------------------- | ------------------ | -------- | -------------: | ----------------------------------------------------------------------------------------------------------- |
| `VC_ASYNC_TEXT_PROVIDER_MATRIX`         | {need}`[[id]] <REQ_ASYNC_PROVIDER_EXECUTION>` | System Integration | Replay   |              5 | Every supported adapter family returns the public normalized text contract through async execution.         |
| `VC_ASYNC_STRUCTURED_PROVIDER_MATRIX`   | {need}`[[id]] <REQ_ASYNC_PROVIDER_EXECUTION>` | System Integration | Replay   |              5 | Every JSON-schema-capable adapter family returns schema-valid structured data through async execution.      |
| `VC_ASYNC_IMAGE_PROVIDER_MATRIX`        | {need}`[[id]] <REQ_ASYNC_PROVIDER_EXECUTION>` | System Integration | Replay   |              5 | Every image-capable adapter family preserves grounded structured image semantics through async execution.   |
| `VC_ASYNC_DOCUMENT_PROVIDER_MATRIX`     | {need}`[[id]] <REQ_ASYNC_PROVIDER_EXECUTION>` | System Integration | Replay   |              4 | Every file-capable adapter family preserves grounded structured document semantics through async execution. |
| `VC_ASYNC_VIDEO_LOCAL_PROVIDER_MATRIX`  | {need}`[[id]] <REQ_ASYNC_PROVIDER_EXECUTION>` | System Integration | Replay   |              4 | Every video-capable adapter family preserves local-video semantics through async execution.                 |
| `VC_ASYNC_VIDEO_REMOTE_PROVIDER_MATRIX` | {need}`[[id]] <REQ_ASYNC_PROVIDER_EXECUTION>` | System Integration | Replay   |              4 | Every video-capable adapter family preserves remote-video semantics through async execution.                |

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

| Group                 | Why                                                                                                            |
| --------------------- | -------------------------------------------------------------------------------------------------------------- |
| Implementation        | Async dispatch/await control flow must preserve the result; numeric comparison/boundary behavior is secondary. |
| Runtime / dependency  | Retry/availability behavior belongs to resilience/routing rather than this successful async-capability claim.  |
| Interface / protocol  | Provider response shape must normalize correctly; error/extra-interaction behavior is covered elsewhere.       |
| Architecture          | No particular async implementation layering is normative.                                                      |
| Specification / model | Wrong public result or omission of a provider/capability partition violates the Requirement.                   |

No blocking mutation threshold is selected; required deterministic fault classes remain
blocking.

(verification-profile-req-response-normalization)=

## Profile · REQ_RESPONSE_NORMALIZATION

**Verification intent.** Prove local normalization of every supported usage shape and
compare semantically equivalent replies from independently shaped provider families at
the public router boundary.

**Models:** {ref}`Provider response normalization <test-plan-response-normalization-model>`

### Required coverage

| Test level         | Boundary   | Representation | M&S target |          Target |
| ------------------ | ---------- | -------------- | ---------- | --------------: |
| Component          | Local      | Actual         | —          | **1 criterion** |
| System Integration | Substitute | Surrogate      | L0         | **1 criterion** |

**Coverage basis.** Usage normalization requires OpenAI mapping, Google object, and
nested mapping partitions. Public equivalence uses OpenAI-compatible as the canonical
baseline and requires one independent comparison for every other supported adapter
family: QwenChat, AI Studio, Gemini WebAPI, and Google GenAI. The denominator is
therefore four retained cross-family paths, not one representative pair.

**Representation basis.** Usage tests execute the actual local normalizer. Public
equivalence executes actual router/adapters against two scripted provider boundaries,
so external participants remain Surrogate/L0.

### Verification criteria

| Criterion                          | Contract                                    | Test level         | Boundary   | Required paths | Success criterion                                                                                                                                                    |
| ---------------------------------- | ------------------------------------------- | ------------------ | ---------- | -------------: | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `VC_PROVIDER_USAGE_NORMALIZATION`  | {need}`[[id]] <TREQ_USAGE_NORMALIZATION>`   | Component          | Local      |              3 | OpenAI mapping, Google object, and nested usage shapes produce the stable usage model with a consistent total.                                                       |
| `VC_PROVIDER_RESPONSE_EQUIVALENCE` | {need}`[[id]] <REQ_RESPONSE_NORMALIZATION>` | System Integration | Substitute |              4 | Each non-baseline provider family exposes public text/usage/tool semantics equivalent to the OpenAI-compatible baseline without provider-specific transport leakage. |

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

| REQUIRED                                                                                           | OPTIONAL          | N/A                                                                                                                                                                                                                                                                          |
| -------------------------------------------------------------------------------------------------- | ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `impl.control-flow` · `interface.payload-schema` · `spec.wrong-outcome` · `spec.missing-partition` | `impl.comparison` | `impl.boundary` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.unexpected-interaction` · `interface.error-status` · `architecture.forbidden-edge` · `architecture.layer-bypass` · `spec.wrong-ordering-boundary` |

#### Fault-group rationale

| Group                 | Why                                                                                                               |
| --------------------- | ----------------------------------------------------------------------------------------------------------------- |
| Implementation        | Shape-selection branches implement normalization; numeric boundary semantics are not part of the public contract. |
| Runtime / dependency  | This profile compares successful replies; transport failures belong to the provider-error contract.               |
| Interface / protocol  | Provider payload shape is the input partition; extra interactions and error statuses are outside this claim.      |
| Architecture          | No internal normalization topology is prescribed.                                                                 |
| Specification / model | Wrong normalized values or a missing supported usage/provider-shape partition invalidates portability.            |

No blocking mutation threshold is selected; required deterministic fault classes remain
blocking.

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

**Coverage basis.** The transport-family denominator is two: one OpenAI-compatible
HTTP failure and one Google GenAI SDK-originated failure, each observed through the
public router and each proving exactly one provider interaction.

**Representation basis.** Both paths execute actual llm-router/provider integration.
The HTTP path uses the scripted provider directly; the SDK path uses the actual Google
GenAI SDK redirected to the scripted provider. External behavior remains Surrogate/L0.

### Verification criteria

| Criterion                | Contract                                     | Test level         | Boundary   | Required paths | Success criterion                                                                                                         |
| ------------------------ | -------------------------------------------- | ------------------ | ---------- | -------------: | ------------------------------------------------------------------------------------------------------------------------- |
| `VC_PROVIDER_ERROR_HTTP` | {need}`[[id]] <REQ_PROVIDER_ERROR_BOUNDARY>` | System Integration | Substitute |              1 | An HTTP rejection becomes ProviderError with stable status metadata, hides provider detail, and performs one request.     |
| `VC_PROVIDER_ERROR_SDK`  | {need}`[[id]] <REQ_PROVIDER_ERROR_BOUNDARY>` | System Integration | Substitute |              1 | A failure raised through the real Google GenAI SDK becomes the same public ProviderError shape with one provider request. |

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

| Group                 | Why                                                                                                                 |
| --------------------- | ------------------------------------------------------------------------------------------------------------------- |
| Implementation        | Exception-translation control flow must converge on ProviderError; comparison/boundary arithmetic is not normative. |
| Runtime / dependency  | Timeout and disconnect are provider failures that must not leak dependency-specific exception types.                |
| Interface / protocol  | Error status is the direct interface stimulus; malformed successful payloads belong to response/adapter contracts.  |
| Architecture          | The public error type is normative, not a particular internal module edge.                                          |
| Specification / model | Both HTTP and SDK transport families must be represented and produce the same public failure category.              |

No blocking mutation threshold is selected; required deterministic fault classes remain
blocking.
