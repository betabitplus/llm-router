(verification-profiles-security)=

# Verification profiles · Data safety

These profiles own verification design for {need}`GOAL_DATA_SAFETY`.
Normative confidentiality semantics remain in the Requirement and Technical
requirements. The parent Requirement proves one product-level observability outcome;
technical leak partitions remain owned by the narrowest TREQ that defines them.

(verification-profile-req-sensitive-data-protection)=

## Profile · REQ_SENSITIVE_DATA_PROTECTION

**Verification intent.** Prove the public confidentiality outcome across the two
observable artifact classes in one representative flow: runtime diagnostics and a
physically retained replay cassette must both remain free of caller/provider protected
values. Detailed logging and recorder mechanics are owned by the derived Technical
requirements and are not duplicated here.

**Models:** {ref}`Data-safety observability audit <test-plan-data-safety-observability-audit-model>`

### Required coverage

| Test level         | Boundary   | Representation | M&S target |          Target |
| ------------------ | ---------- | -------------- | ---------- | --------------: |
| System Integration | Substitute | Surrogate      | L0         | **1 criterion** |

**Coverage basis.** The Requirement asserts one product-level outcome: a representative
public request may be observed and recorded without protected prompt, credential, tool
argument, or tool-result values becoming durable observability artifacts. Detailed
provider/tool/schema diagnostics and VCR scrub partitions are technical support, not
additional parent criteria.

**Representation basis.** The audit executes the real public router, runtime logging,
tool orchestration, provider adapter, VCR pre-serialization scrub, physical cassette
write, and replay-capable recorder against a deterministic scripted provider.
Surrogate/L0 is sufficient because confidentiality of local artifacts does not depend on
external provider reasoning.

### Verification criteria

| Criterion                            | Contract                                       | Test level         | Boundary   | Required paths | Success criterion                                                                                                                                                                                                    |
| ------------------------------------ | ---------------------------------------------- | ------------------ | ---------- | -------------: | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `VC_DATA_SAFETY_OBSERVABILITY_AUDIT` | {need}`[[id]] <REQ_SENSITIVE_DATA_PROTECTION>` | System Integration | Substitute |              1 | One representative public tool request completes while protected prompt, credential, tool argument, and tool-result markers are absent from every retained runtime log field and the physically serialized cassette. |

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

| Technical requirement                                                                                            | Target |
| ---------------------------------------------------------------------------------------------------------------- | ------ |
| {need}`Runtime diagnostics expose only safe metadata <TREQ_RUNTIME_LOG_SAFETY>`                                  | PASS   |
| {need}`VCR recordings remove provider authentication <TREQ_VCR_AUTH_REDACTION>`                                  | PASS   |
| {need}`VCR request records persist fingerprints instead of caller payloads <TREQ_VCR_REQUEST_CONTENT_REDACTION>` | PASS   |
| {need}`VCR response records remove caller-controlled echoes <TREQ_VCR_RESPONSE_CONTENT_REDACTION>`               | PASS   |

### Fault applicability

| REQUIRED                                                                         | OPTIONAL                    | N/A                                                                                                                                                                                                                                                                                  |
| -------------------------------------------------------------------------------- | --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `spec.wrong-outcome` · `spec.missing-partition` · `spec.wrong-ordering-boundary` | `architecture.layer-bypass` | `impl.comparison` · `impl.boundary` · `impl.control-flow` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.unexpected-interaction` · `interface.error-status` · `interface.payload-schema` · `architecture.forbidden-edge` |

#### Fault-group rationale

| Group                 | Why                                                                                                                                                                      |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Implementation        | Concrete redaction branches belong to the derived Technical requirements; the parent constrains the combined observable outcome rather than one implementation decision. |
| Runtime / dependency  | Dependency failure partitions are verified by the runtime-diagnostics TREQ; the parent outcome does not require a separate duplicate runtime fault campaign.             |
| Interface / protocol  | Provider/auth/body protocol details belong to the corresponding Technical requirements.                                                                                  |
| Architecture          | A bypass of all required sanitization layers could violate the combined outcome and is worth observing, but the parent does not prescribe one package dependency edge.   |
| Specification / model | Wrong retained content, a missing artifact partition, or sanitization occurring only after persistence directly violates the product-level confidentiality outcome.      |

No blocking mutation threshold is selected; required deterministic fault obligations remain
blocking.

(verification-profile-treq-runtime-log-safety)=

## Profile · TREQ_RUNTIME_LOG_SAFETY

**Verification intent.** Prove that runtime logging and public failure surfaces expose
only bounded safe metadata across the independent provider, local-tool, and
schema-validation failure partitions.

**Models:** {ref}`Sensitive runtime diagnostics <test-plan-sensitive-runtime-diagnostics-model>`

### Required coverage

| Test level         | Boundary   | Representation | M&S target |          Target |
| ------------------ | ---------- | -------------- | ---------- | --------------: |
| Component          | Local      | Actual         | —          | **1 criterion** |
| System Integration | Substitute | Surrogate      | L0         |  **3 criteria** |

**Coverage basis.** Safe log-context selection is one local policy criterion. Public
failures have three independent leak partitions because provider error payloads,
tool-cause/argument data, and schema-invalid caller values cross different runtime
exception paths.

**Representation basis.** The component criterion executes the actual safe-field
implementation. System-integration paths execute the real public router/runtime/provider
adapter against a deterministic scripted provider. Surrogate/L0 is sufficient because
the contract concerns local logging/error behavior.

### Verification criteria

| Criterion                                  | Contract                                 | Test level         | Boundary   | Required paths | Success criterion                                                                                                                                                              |
| ------------------------------------------ | ---------------------------------------- | ------------------ | ---------- | -------------: | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `VC_SECURITY_LOG_CONTEXT_FIELDS`           | {need}`[[id]] <TREQ_RUNTIME_LOG_SAFETY>` | Component          | Local      |              1 | Provider request log context exposes only declared safe identifiers and cannot contain credentials, messages, provider kwargs, schema data, or tool payloads.                  |
| `VC_SECURITY_PROVIDER_FAILURE_DIAGNOSTICS` | {need}`[[id]] <TREQ_RUNTIME_LOG_SAFETY>` | System Integration | Substitute |              1 | Provider-controlled error text, credentials, and prompt content are absent from the public error and every retained runtime log field while safe status/type metadata remains. |
| `VC_SECURITY_TOOL_FAILURE_DIAGNOSTICS`     | {need}`[[id]] <TREQ_RUNTIME_LOG_SAFETY>` | System Integration | Substitute |              1 | Prompt, credential, tool arguments, and tool-cause text are absent from the public tool failure and every retained runtime log field while safe tool/type metadata remains.    |
| `VC_SECURITY_SCHEMA_FAILURE_DIAGNOSTICS`   | {need}`[[id]] <TREQ_RUNTIME_LOG_SAFETY>` | System Integration | Substitute |              1 | Schema-invalid values, caller schema identifiers, credentials, and validation detail are absent from the public exhausted-repair error and every retained runtime log field.   |

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

| REQUIRED                                                                                                                                                                                                                      | OPTIONAL                            | N/A                                                                                                                             |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `impl.control-flow` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.error-status` · `interface.payload-schema` · `architecture.layer-bypass` · `spec.wrong-outcome` · `spec.missing-partition` | `impl.comparison` · `impl.boundary` | `runtime.latency-timeout` · `interface.unexpected-interaction` · `architecture.forbidden-edge` · `spec.wrong-ordering-boundary` |

#### Fault-group rationale

| Group                 | Why                                                                                                                                                                                       |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Implementation        | Safe-field and exception-flow branches decide whether protected values enter diagnostics; comparison/boundary mutations can be useful but are not defining confidentiality partitions.    |
| Runtime / dependency  | Disconnect and malformed-response paths can surface raw dependency detail; latency without failure does not independently change the leak boundary.                                       |
| Interface / protocol  | Error-status bodies and schema-invalid payloads are explicit hostile/sensitive partitions; an extra interaction is a routing concern rather than this diagnostic-content claim.           |
| Architecture          | Bypassing the centralized safe diagnostic boundary can leak even when helper-level tests pass; no package dependency edge is itself normative.                                            |
| Specification / model | Wrong diagnostic content or omission of provider/tool/schema partitions directly violates this Technical requirement; ordering before persistence belongs to the VCR technical contracts. |

No blocking mutation threshold is selected; required deterministic fault obligations remain
blocking.

(verification-profile-treq-vcr-auth-redaction)=

## Profile · TREQ_VCR_AUTH_REDACTION

**Verification intent.** Prove that authentication headers, cookies, response cookies,
and provider/account identity material are removed before a cassette becomes durable,
while safe replay metadata remains usable.

**Models:** {ref}`Durable VCR redaction <test-plan-vcr-redaction-model>`

### Required coverage

| Test level         | Boundary   | Representation | M&S target |          Target |
| ------------------ | ---------- | -------------- | ---------- | --------------: |
| System Integration | Substitute | Surrogate      | L0         | **1 criterion** |

**Coverage basis.** Authentication/account material is one durable-redaction contract.
Its proof must inspect the physical cassette after recording and prove replay still
works; in-memory scrub output alone is insufficient.

**Representation basis.** The path executes the actual router/provider request,
pre-serialization VCR filters, filesystem persistence, and offline replay against a
deterministic local HTTP substitute. Surrogate/L0 is appropriate because the provider's
semantic reasoning is outside this claim.

### Verification criteria

| Criterion                       | Contract                                 | Test level         | Boundary   | Required paths | Success criterion                                                                                                                                             |
| ------------------------------- | ---------------------------------------- | ------------------ | ---------- | -------------: | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `VC_VCR_AUTH_DURABLE_REDACTION` | {need}`[[id]] <TREQ_VCR_AUTH_REDACTION>` | System Integration | Substitute |              1 | A physically serialized cassette removes request/response authentication and account PII, preserves explicitly safe metadata, and remains replayable offline. |

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

| REQUIRED                                                                                                                                                          | OPTIONAL          | N/A                                                                                                                                                                                                           |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `impl.control-flow` · `interface.payload-schema` · `architecture.layer-bypass` · `spec.wrong-outcome` · `spec.missing-partition` · `spec.wrong-ordering-boundary` | `impl.comparison` | `impl.boundary` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.unexpected-interaction` · `interface.error-status` · `architecture.forbidden-edge` |

#### Fault-group rationale

| Group                 | Why                                                                                                                                                             |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Implementation        | Scrub control flow decides whether protected headers/account fields survive; threshold-style boundaries are not part of the contract.                           |
| Runtime / dependency  | Recorder confidentiality is about pre-persistence transformation, not dependency timing or availability.                                                        |
| Interface / protocol  | Authentication/account material arrives in protocol fields and response payload shapes; HTTP success vs error status is not itself the redaction requirement.   |
| Architecture          | Bypassing the pre-serialization scrub layer would expose secrets; no particular package dependency edge is normative.                                           |
| Specification / model | Persisting protected material, omitting an auth/account partition, or scrubbing only after the cassette is written directly violates the Technical requirement. |

No blocking mutation threshold is selected; required deterministic fault obligations remain
blocking.

(verification-profile-treq-vcr-request-content-redaction)=

## Profile · TREQ_VCR_REQUEST_CONTENT_REDACTION

**Verification intent.** Prove that raw caller request/tool content is replaced by a
stable non-reversible request fingerprint before physical cassette serialization while
offline replay discrimination remains intact.

**Models:** {ref}`Durable VCR redaction <test-plan-vcr-redaction-model>`

### Required coverage

| Test level         | Boundary   | Representation | M&S target |          Target |
| ------------------ | ---------- | -------------- | ---------- | --------------: |
| System Integration | Substitute | Surrogate      | L0         | **1 criterion** |

**Coverage basis.** Raw request-body persistence is one technical obligation. The proof
must inspect serialized request bodies and then replay the original request after the
live server is gone so secrecy is not obtained by destroying replay identity.

**Representation basis.** The path executes the actual router/tool loop, provider
adapter, request fingerprinting, physical VCR serialization, and offline replay against
a deterministic local HTTP substitute. External provider semantics are not part of the
claim, so Surrogate/L0 is appropriate.

### Verification criteria

| Criterion                               | Contract                                            | Test level         | Boundary   | Required paths | Success criterion                                                                                                                                                                       |
| --------------------------------------- | --------------------------------------------------- | ------------------ | ---------- | -------------: | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `VC_VCR_REQUEST_BODY_DURABLE_REDACTION` | {need}`[[id]] <TREQ_VCR_REQUEST_CONTENT_REDACTION>` | System Integration | Substitute |              1 | Every physically serialized request body is a deterministic non-reversible fingerprint instead of raw caller prompt/tool payload, and the original request still matches during replay. |

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

| REQUIRED                                                                                                                             | OPTIONAL          | N/A                                                                                                                                                                                                                                        |
| ------------------------------------------------------------------------------------------------------------------------------------ | ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `impl.control-flow` · `architecture.layer-bypass` · `spec.wrong-outcome` · `spec.missing-partition` · `spec.wrong-ordering-boundary` | `impl.comparison` | `impl.boundary` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.unexpected-interaction` · `interface.error-status` · `interface.payload-schema` · `architecture.forbidden-edge` |

#### Fault-group rationale

| Group                 | Why                                                                                                                                                                        |
| --------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Implementation        | Request-body replacement control flow determines whether raw content is persisted; numeric thresholds are not part of the contract.                                        |
| Runtime / dependency  | Fingerprinting/persistence semantics are local recorder behavior and do not depend on dependency timing or availability.                                                   |
| Interface / protocol  | The contract intentionally hashes the complete raw request body regardless of its provider-specific schema, so protocol-shape faults are not separate required partitions. |
| Architecture          | Bypassing the pre-serialization request scrub layer would persist raw content; no particular package dependency edge is normative.                                         |
| Specification / model | Raw content persistence, omission of a request/tool partition, or replacement after serialization directly violates the Technical requirement.                             |

No blocking mutation threshold is selected; required deterministic fault obligations remain
blocking.

(verification-profile-treq-vcr-response-content-redaction)=

## Profile · TREQ_VCR_RESPONSE_CONTENT_REDACTION

**Verification intent.** Prove that caller-controlled values echoed by provider response
payloads are replaced before physical cassette persistence without destroying the
response shape needed to replay router/tool behavior.

**Models:** {ref}`Durable VCR redaction <test-plan-vcr-redaction-model>`

### Required coverage

| Test level         | Boundary   | Representation | M&S target |          Target |
| ------------------ | ---------- | -------------- | ---------- | --------------: |
| System Integration | Substitute | Surrogate      | L0         | **1 criterion** |

**Coverage basis.** Provider responses form a separate durable ingress path from outbound
request bodies. One focused criterion must prove a caller-controlled tool argument echoed
by the provider is absent from the physical cassette and replay still preserves the
tool-call structure.

**Representation basis.** The path executes the actual router/tool loop, provider
adapter, response scrub, physical VCR serialization, and offline replay against a
deterministic local HTTP substitute. External provider reasoning is not part of the
claim, so Surrogate/L0 is appropriate.

### Verification criteria

| Criterion                                | Contract                                             | Test level         | Boundary   | Required paths | Success criterion                                                                                                                                                                                   |
| ---------------------------------------- | ---------------------------------------------------- | ------------------ | ---------- | -------------: | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `VC_VCR_RESPONSE_ECHO_DURABLE_REDACTION` | {need}`[[id]] <TREQ_VCR_RESPONSE_CONTENT_REDACTION>` | System Integration | Substitute |              1 | A caller-controlled value echoed in a provider tool-call response is absent from the physically serialized cassette, and offline replay retains a structurally valid tool call and successful flow. |

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

| REQUIRED                                                                                                                                                          | OPTIONAL          | N/A                                                                                                                                                                                                           |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `impl.control-flow` · `interface.payload-schema` · `architecture.layer-bypass` · `spec.wrong-outcome` · `spec.missing-partition` · `spec.wrong-ordering-boundary` | `impl.comparison` | `impl.boundary` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.unexpected-interaction` · `interface.error-status` · `architecture.forbidden-edge` |

#### Fault-group rationale

| Group                 | Why                                                                                                                                             |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| Implementation        | Response-scrub control flow decides whether reflected protected values survive; threshold-style boundaries are not part of the contract.        |
| Runtime / dependency  | The confidentiality boundary is local pre-persistence transformation rather than dependency timing or availability.                             |
| Interface / protocol  | Provider response payload shape is the ingress that may carry echoed caller values; HTTP status itself is not the confidentiality partition.    |
| Architecture          | Bypassing the response scrub before serialization would retain raw values; no package dependency edge is itself normative.                      |
| Specification / model | Persisting the echo, omitting the response-echo partition, or sanitizing only after serialization directly violates this Technical requirement. |

No blocking mutation threshold is selected; required deterministic fault obligations remain
blocking.
