(verification-profiles-resilience)=

# Verification profiles · Resilient execution

These profiles own verification design for the parent contracts in
{need}`GOAL_RESILIENT_EXECUTION`. Product semantics remain in the normative
Requirements and Technical requirements. Targets are derived from recovery risks and
public execution semantics, not from the test set that already exists.

(verification-profile-req-provider-retry)=

## Profile · REQ_PROVIDER_RETRY

**Verification intent.** Prove that retry classification is semantic rather than
message-based, that transient/permanent outcomes behave the same through synchronous
and asynchronous public execution, and that same-route provider calls stop at the
configured retry budget before routing can continue.

**Models:** {ref}`Provider retry <test-plan-provider-retry-model>`

### Required coverage

| Test level         | Boundary   | Representation | M&S target |         Target |
| ------------------ | ---------- | -------------- | ---------- | -------------: |
| Component          | Local      | Actual         | —          | **2 criteria** |
| System Integration | Substitute | Surrogate      | L0         | **3 criteria** |

**Coverage basis.** Classification has independent status and exception semantics, each
requiring both retryable and non-retryable partitions. Public execution has three
independent outcomes — transient recovery, permanent rejection, and exhausted retry
budget — and each must hold in both sync and async execution modes.

**Representation basis.** Classification executes actual local policy code. Public
retry workflows execute actual router/provider-adapter code against a deterministic
scripted provider; Surrogate/L0 is sufficient because the claim is retry control flow
and interaction count, not external provider reasoning.

### Verification criteria

| Criterion                                    | Contract                                            | Test level         | Boundary   | Required paths | Required path IDs                             | Success criterion                                                                                                          |
| -------------------------------------------- | --------------------------------------------------- | ------------------ | ---------- | -------------: | --------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| `VC_PROVIDER_RETRY_STATUS_CLASSIFICATION`    | {need}`[[id]] <TREQ_PROVIDER_RETRY_CLASSIFICATION>` | Component          | Local      |              2 | `retryable-status` · `permanent-status`       | Representative retryable and permanent HTTP statuses are classified from status semantics, not text.                       |
| `VC_PROVIDER_RETRY_EXCEPTION_CLASSIFICATION` | {need}`[[id]] <TREQ_PROVIDER_RETRY_CLASSIFICATION>` | Component          | Local      |              2 | `transport-exception` · `unrelated-exception` | A transport exception type is retryable while an unrelated exception with retry-like wording/type fragments is not.        |
| `VC_PROVIDER_RETRY_TRANSIENT_RECOVERY`       | {need}`[[id]] <REQ_PROVIDER_RETRY>`                 | System Integration | Substitute |              2 | `sync` · `async`                              | Sync and async requests both recover from a transient provider failure on the same route without route fallback.           |
| `VC_PROVIDER_RETRY_PERMANENT_NO_RETRY`       | {need}`[[id]] <REQ_PROVIDER_RETRY>`                 | System Integration | Substitute |              2 | `sync` · `async`                              | Sync and async permanent provider failures each produce exactly one provider interaction and no same-route retry.          |
| `VC_PROVIDER_RETRY_ATTEMPT_BOUND`            | {need}`[[id]] <TREQ_PROVIDER_RETRY_BOUNDS>`         | System Integration | Substitute |              2 | `sync` · `async`                              | Sync and async exhausted retry each perform exactly the configured maximum attempt count and never one interaction beyond. |

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

| REQUIRED                                                                                                                                         | OPTIONAL | N/A                                                                                      |
| ------------------------------------------------------------------------------------------------------------------------------------------------ | -------- | ---------------------------------------------------------------------------------------- |
| `impl.comparison` · `impl.boundary` · `impl.control-flow` · `runtime.latency-timeout` · `runtime.unavailable-disconnect`                         | —        | `runtime.malformed-response`                                                             |
| `interface.unexpected-interaction` · `interface.error-status` · `spec.wrong-outcome` · `spec.missing-partition` · `spec.wrong-ordering-boundary` | —        | `interface.payload-schema` · `architecture.forbidden-edge` · `architecture.layer-bypass` |

#### Fault-group rationale

| Group                 | Why                                                                                                                                     |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| Implementation        | Retryability comparisons, attempt-budget boundaries, and retry-loop branches directly determine whether work is retried or stopped.     |
| Runtime / dependency  | Timeout/disconnect are distinct transient transport mechanisms; malformed application payload belongs to other response contracts.      |
| Interface / protocol  | Error status is a primary retry signal, and any provider interaction beyond a permanent failure or configured attempt cap is forbidden. |
| Architecture          | This contract constrains observable retry behavior without requiring a particular internal module topology.                             |
| Specification / model | Transient/permanent, sync/async, and exhausted-budget partitions plus retry-before-surface ordering are normative.                      |

No blocking mutation threshold is selected; required deterministic fault classes remain
blocking.

(verification-profile-req-structured-output-repair)=

## Profile · REQ_STRUCTURED_OUTPUT_REPAIR

**Verification intent.** Prove that invalid structured output can recover, that the
total provider-response budget counts the initial response and every repair turn, and
that dynamic repair-prompt content remains bounded independently of generated input
size.

**Models:** {ref}`Structured-output recovery <test-plan-structured-recovery-model>`

### Required coverage

| Test level         | Boundary   | Representation | M&S target |          Target |
| ------------------ | ---------- | -------------- | ---------- | --------------: |
| Component          | Local      | Actual         | —          | **1 criterion** |
| System Integration | Substitute | Surrogate      | L0         |  **2 criteria** |

**Coverage basis.** Prompt bounds are a property of the local builder and require one
property-based retained path. Public recovery requires one successful repair path plus
two attempt-budget boundary paths: the minimum valid budget of one and an intermediate
budget of two. Both boundary paths must prove exact external request counts.

**Representation basis.** Prompt construction executes actual local code. Public
recovery executes actual router/provider-adapter/schema-validation code against a
scripted provider that deliberately returns schema-invalid payloads; Surrogate/L0 is
sufficient because the claim is local repair state and interaction count.

### Verification criteria

| Criterion                            | Contract                                               | Test level         | Boundary   | Required paths | Required path IDs       | Success criterion                                                                                                         |
| ------------------------------------ | ------------------------------------------------------ | ------------------ | ---------- | -------------: | ----------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `VC_REPAIR_PROMPT_BOUNDS`            | {need}`[[id]] <TREQ_REPAIR_PROMPT_BOUNDS>`             | Component          | Local      |              1 | —                       | Property-generated schema identity, invalid output, and validation detail cannot expand the repair prompt beyond its cap. |
| `VC_STRUCTURED_REPAIR_RECOVERY`      | {need}`[[id]] <REQ_STRUCTURED_OUTPUT_REPAIR>`          | System Integration | Substitute |              1 | —                       | With total attempt budget 2, an invalid first response followed by valid output succeeds on the final allowed response.   |
| `VC_STRUCTURED_REPAIR_ATTEMPT_BOUND` | {need}`[[id]] <TREQ_STRUCTURED_OUTPUT_ATTEMPT_BOUNDS>` | System Integration | Substitute |              2 | `budget-1` · `budget-2` | Budgets 1 and 2 each stop after exactly that many invalid provider responses and expose the public structured error.      |

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

| REQUIRED                                                                                                                    | OPTIONAL | N/A                                                                                         |
| --------------------------------------------------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------- |
| `impl.comparison` · `impl.boundary` · `impl.control-flow` · `interface.unexpected-interaction` · `interface.payload-schema` | —        | `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` |
| `spec.wrong-outcome` · `spec.missing-partition` · `spec.wrong-ordering-boundary`                                            | —        | `interface.error-status` · `architecture.forbidden-edge` · `architecture.layer-bypass`      |

#### Fault-group rationale

| Group                 | Why                                                                                                                             |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| Implementation        | Attempt-count comparisons, cap boundaries, and repair/raise control flow directly implement bounded recovery.                   |
| Runtime / dependency  | Recovery is triggered by schema-invalid successful responses, not transport latency/disconnect or malformed HTTP transport.     |
| Interface / protocol  | Schema-invalid payload is the recovery stimulus, and any provider call beyond the configured total-attempt budget is forbidden. |
| Architecture          | The contract does not prescribe a particular internal module topology.                                                          |
| Specification / model | Success/exhaustion partitions, minimum/intermediate budgets, and invalid→repair→success/failure ordering are normative.         |

No blocking mutation threshold is selected; required deterministic fault classes remain
blocking.
