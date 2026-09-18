(verification-profiles-security)=

# Verification profile · Data safety

This profile owns verification design for the parent contract in
{need}`GOAL_DATA_SAFETY`. Product semantics remain in the normative Requirement
and Technical requirements. The target is derived from the durable-artifact and
diagnostic leak surfaces, not from the security tests that already exist.

(verification-profile-req-sensitive-data-protection)=

## Profile · REQ_SENSITIVE_DATA_PROTECTION

**Verification intent.** Prove that protected values do not cross either durable
observability boundary: runtime/public failure diagnostics or retained HTTP replay
evidence. The proof must exercise provider, tool, schema-validation, authentication,
and raw request-body partitions because each has a distinct serialization path.

**Models:** {ref}`Sensitive runtime diagnostics <test-plan-sensitive-runtime-diagnostics-model>` ·
{ref}`Durable VCR redaction <test-plan-vcr-redaction-model>`

### Required coverage

| Test level         | Boundary   | Representation | M&S target |          Target |
| ------------------ | ---------- | -------------- | ---------- | --------------: |
| Component          | Local      | Actual         | —          | **1 criterion** |
| System Integration | Substitute | Surrogate      | L0         |  **5 criteria** |

**Coverage basis.** Safe field selection is a local policy and needs one focused
component proof. Durable VCR safety has two independent contracts: authentication/
account material and raw request/tool payload persistence. Public runtime diagnostics
have three independent leak paths: provider failure payloads, local tool failures,
and schema-validation failures.

**Representation basis.** Component policy evidence executes the actual local
safe-field implementation. Durable recorder and public diagnostic paths execute the
actual router/runtime/provider adapter and VCR serialization stack against a
deterministic scripted provider. Surrogate/L0 is sufficient because the claim is local
serialization/logging/error behavior, not external provider reasoning.

### Verification criteria

| Criterion                                  | Contract                                            | Test level         | Boundary   | Required paths | Success criterion                                                                                                                                                                           |
| ------------------------------------------ | --------------------------------------------------- | ------------------ | ---------- | -------------: | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `VC_SECURITY_LOG_CONTEXT_FIELDS`           | {need}`[[id]] <TREQ_RUNTIME_LOG_SAFETY>`            | Component          | Local      |              1 | Provider request log context exposes only the declared safe identifiers and cannot contain credential values, messages, kwargs, schema data, or tool payloads.                              |
| `VC_VCR_AUTH_DURABLE_REDACTION`            | {need}`[[id]] <TREQ_VCR_AUTH_REDACTION>`            | System Integration | Substitute |              1 | A physically serialized cassette removes request/response authentication and account PII while preserving replay-relevant safe metadata and remains replayable.                             |
| `VC_VCR_REQUEST_BODY_DURABLE_REDACTION`    | {need}`[[id]] <TREQ_VCR_REQUEST_CONTENT_REDACTION>` | System Integration | Substitute |              1 | A physically serialized cassette contains a deterministic non-reversible request-body fingerprint instead of raw caller prompt/tool payload, and replay still matches the original request. |
| `VC_SECURITY_PROVIDER_FAILURE_DIAGNOSTICS` | {need}`[[id]] <TREQ_RUNTIME_LOG_SAFETY>`            | System Integration | Substitute |              1 | Provider-controlled error text and credentials are absent from the public error and every retained runtime log field while safe status/type metadata remains available.                     |
| `VC_SECURITY_TOOL_FAILURE_DIAGNOSTICS`     | {need}`[[id]] <TREQ_RUNTIME_LOG_SAFETY>`            | System Integration | Substitute |              1 | Prompt, credential, tool arguments, and tool-cause text are absent from the public tool failure and every retained runtime log field while tool/type metadata remains available.            |
| `VC_SECURITY_SCHEMA_FAILURE_DIAGNOSTICS`   | {need}`[[id]] <TREQ_RUNTIME_LOG_SAFETY>`            | System Integration | Substitute |              1 | Schema-invalid values, caller schema identifiers, credentials, and validation detail are absent from the public exhausted-repair error and every retained runtime log field.                |

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

| REQUIRED                                                                                                                                                          | OPTIONAL        | N/A                                                            |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------- | -------------------------------------------------------------- |
| `impl.comparison` · `impl.control-flow` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.error-status` · `interface.payload-schema` | `impl.boundary` | `runtime.latency-timeout` · `interface.unexpected-interaction` |
| `architecture.layer-bypass` · `spec.wrong-outcome` · `spec.missing-partition` · `spec.wrong-ordering-boundary`                                                    | —               | `architecture.forbidden-edge`                                  |

#### Fault-group rationale

| Group                 | Why                                                                                                                                                                                                     |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Implementation        | Redaction/safe-field selection and exception-flow branches directly decide whether protected values reach an artifact; numeric boundary mutation is secondary rather than a defining secrecy partition. |
| Runtime / dependency  | Disconnect and malformed-response failures exercise distinct raw-exception/body paths that can leak. Latency without failure does not change the data-safety claim.                                     |
| Interface / protocol  | Provider error bodies and schema-invalid payloads are direct hostile/sensitive inputs. Extra provider calls are a routing concern, not the confidentiality outcome asserted here.                       |
| Architecture          | Bypassing the centralized safe log context or VCR pre-serialization scrub layer can leak even when the helpers themselves are correct. No particular module dependency edge is itself normative.        |
| Specification / model | Provider/tool/schema partitions must all be present, protected values must remain absent, and VCR redaction must happen before durable serialization rather than after the cassette is written.         |

No blocking mutation threshold is selected; required deterministic fault classes remain
blocking.
