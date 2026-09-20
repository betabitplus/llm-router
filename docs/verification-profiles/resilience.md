(verification-profiles-resilience)=

# Verification profiles · Resilient execution

These profiles own verification design for the contracts under
{need}`GOAL_RESILIENT_EXECUTION`. Product semantics remain in the normative
Requirements and Technical requirements. Targets are derived from recovery risks and
public execution semantics, not from the test set that already exists.

(verification-profile-req-provider-retry)=

## Profile · REQ_PROVIDER_RETRY

**Verification intent.** Prove through the public execution path that temporary provider
failures can recover on the same route, permanent provider failures are not retried, and
the parent claim remains dependent on explicit retry classification and bounded retry
work owned by its Technical requirements.

**Models:** {ref}`Provider retry <test-plan-provider-retry-model>`

### Required coverage

| Test level         | Boundary   | Representation | M&S target |         Target |
| ------------------ | ---------- | -------------- | ---------- | -------------: |
| System Integration | Substitute | Surrogate      | L0         | **2 criteria** |

**Coverage basis.** Temporary recovery must be exercised in sync and async execution for
both a retryable HTTP-status failure and a transient transport failure. Permanent
rejection must be exercised in sync and async execution and prove exactly one provider
interaction. Internal classification partitions and the configured attempt ceiling are
owned by the child Technical requirements.

**Representation basis.** Public retry workflows execute actual
router/provider-adapter code against a deterministic scripted provider participant;
Surrogate/L0 is sufficient because the claim is retry control flow and interaction
count, not external provider reasoning.

### Verification criteria

| Criterion                              | Contract                            | Test level         | Boundary   | Required paths | Required path IDs                                                     | Success criterion                                                                                                     |
| -------------------------------------- | ----------------------------------- | ------------------ | ---------- | -------------: | --------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `VC_PROVIDER_RETRY_TRANSIENT_RECOVERY` | {need}`[[id]] <REQ_PROVIDER_RETRY>` | System Integration | Substitute |              4 | `sync-status` · `async-status` · `sync-transport` · `async-transport` | Sync and async public requests recover on the same route from representative retryable status and transport failures. |
| `VC_PROVIDER_RETRY_PERMANENT_NO_RETRY` | {need}`[[id]] <REQ_PROVIDER_RETRY>` | System Integration | Substitute |              2 | `sync-status` · `async-status`                                        | Sync and async permanent provider failures each produce exactly one provider interaction and no same-route retry.     |

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

| Technical requirement                                                                             | Target |
| ------------------------------------------------------------------------------------------------- | ------ |
| {need}`Retry classification uses explicit failure semantics <TREQ_PROVIDER_RETRY_CLASSIFICATION>` | PASS   |
| {need}`Same-route provider retry is bounded <TREQ_PROVIDER_RETRY_BOUNDS>`                         | PASS   |

### Fault applicability

| REQUIRED                                                                                                                     | OPTIONAL | N/A                                                                                                                   |
| ---------------------------------------------------------------------------------------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------- |
| `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `interface.error-status` · `interface.unexpected-interaction` | —        | `impl.comparison` · `impl.boundary` · `impl.control-flow` · `runtime.malformed-response` · `interface.payload-schema` |
| `spec.wrong-outcome` · `spec.missing-partition`                                                                              | —        | `architecture.forbidden-edge` · `architecture.layer-bypass` · `spec.wrong-ordering-boundary`                          |

#### Fault-group rationale

| Group                 | Why                                                                                                                       |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| Implementation        | Retry classifier and attempt-loop implementation faults are owned by the child Technical requirements.                    |
| Runtime / dependency  | Timeout/disconnect are representative transient provider failures whose public recovery behavior must remain correct.     |
| Interface / protocol  | Provider error status and absence of an unexpected extra interaction are observable parts of retry behavior.              |
| Architecture          | The parent contract does not prescribe internal module layering.                                                          |
| Specification / model | Temporary/permanent and sync/async partitions are normative product behavior; missing one can hide a public recovery gap. |

No blocking mutation threshold is selected; required deterministic fault classes remain
blocking.

(verification-profile-treq-provider-retry-classification)=

## Profile · TREQ_PROVIDER_RETRY_CLASSIFICATION

**Verification intent.** Prove that local retry classification uses explicit status and
exception semantics and rejects retry-like text/name coincidences.

**Models:** {ref}`Provider retry <test-plan-provider-retry-model>`

### Required coverage

| Test level | Boundary | Representation | M&S target |         Target |
| ---------- | -------- | -------------- | ---------- | -------------: |
| Component  | Local    | Actual         | —          | **2 criteria** |

**Coverage basis.** Status classification and exception classification are independent
semantic obligations. Each requires one retryable and one non-retryable partition so
message/name coincidences cannot satisfy the target accidentally.

**Representation basis.** All paths execute the actual local retry classifier against
native status values and exception types; no external participant or model substitute is
involved.

### Verification criteria

| Criterion                                    | Contract                                            | Test level | Boundary | Required paths | Required path IDs                             | Success criterion                                                                                            |
| -------------------------------------------- | --------------------------------------------------- | ---------- | -------- | -------------: | --------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| `VC_PROVIDER_RETRY_STATUS_CLASSIFICATION`    | {need}`[[id]] <TREQ_PROVIDER_RETRY_CLASSIFICATION>` | Component  | Local    |              2 | `retryable-status` · `permanent-status`       | Representative retryable and permanent HTTP statuses are classified from status semantics, not message text. |
| `VC_PROVIDER_RETRY_EXCEPTION_CLASSIFICATION` | {need}`[[id]] <TREQ_PROVIDER_RETRY_CLASSIFICATION>` | Component  | Local    |              2 | `transport-exception` · `unrelated-exception` | A transport exception type is retryable while an unrelated retry-like exception is rejected.                 |

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

| REQUIRED                                                       | OPTIONAL | N/A                                                                                                                                                                   |
| -------------------------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `impl.comparison` · `impl.control-flow` · `spec.wrong-outcome` | —        | `impl.boundary` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.error-status` · `interface.payload-schema` |
| `spec.missing-partition`                                       | —        | `interface.unexpected-interaction` · `architecture.forbidden-edge` · `architecture.layer-bypass` · `spec.wrong-ordering-boundary`                                     |

#### Fault-group rationale

| Group                 | Why                                                                                                                                |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| Implementation        | Retryability comparisons and classifier branches directly determine the classification result.                                     |
| Runtime / dependency  | External transport failures are classifier inputs, not external dependencies exercised by this local contract.                     |
| Interface / protocol  | The Technical requirement consumes normalized status/exception semantics rather than owning an external protocol boundary.         |
| Architecture          | Classification correctness does not prescribe a specific module topology.                                                          |
| Specification / model | Retryable/permanent status and transport/unrelated exception partitions are all required; omission or inversion violates the rule. |

No blocking mutation threshold is selected.

(verification-profile-treq-provider-retry-bounds)=

## Profile · TREQ_PROVIDER_RETRY_BOUNDS

**Verification intent.** Prove that one resolved provider route never exceeds the
configured same-route retry maximum and that the initial provider call counts as attempt
one.

**Models:** {ref}`Provider retry <test-plan-provider-retry-model>`

### Required coverage

| Test level         | Boundary   | Representation | M&S target |          Target |
| ------------------ | ---------- | -------------- | ---------- | --------------: |
| System Integration | Substitute | Surrogate      | L0         | **1 criterion** |

**Coverage basis.** The same attempt ceiling must hold in sync and async public
execution, with the initial provider call counted as attempt one in both paths.

**Representation basis.** Actual retry/runtime code is exercised against a scripted
provider boundary; the external participant is therefore Surrogate at L0.

### Verification criteria

| Criterion                         | Contract                                    | Test level         | Boundary   | Required paths | Required path IDs | Success criterion                                                                                                          |
| --------------------------------- | ------------------------------------------- | ------------------ | ---------- | -------------: | ----------------- | -------------------------------------------------------------------------------------------------------------------------- |
| `VC_PROVIDER_RETRY_ATTEMPT_BOUND` | {need}`[[id]] <TREQ_PROVIDER_RETRY_BOUNDS>` | System Integration | Substitute |              2 | `sync` · `async`  | Sync and async exhausted retry each perform exactly the configured maximum attempt count and never one interaction beyond. |

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

| REQUIRED                                                                                       | OPTIONAL | N/A                                                                                                                                                 |
| ---------------------------------------------------------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `impl.comparison` · `impl.boundary` · `impl.control-flow` · `interface.unexpected-interaction` | —        | `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.payload-schema` · `interface.error-status` |
| `spec.wrong-outcome` · `spec.wrong-ordering-boundary`                                          | —        | `architecture.forbidden-edge` · `architecture.layer-bypass` · `spec.missing-partition`                                                              |

#### Fault-group rationale

| Group                 | Why                                                                                                                     |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| Implementation        | Attempt-count comparison, off-by-one boundary, and retry-loop control flow directly implement the cap.                  |
| Runtime / dependency  | Which transient mechanism caused retry is outside this Technical requirement; only the number of attempts matters here. |
| Interface / protocol  | An interaction after the configured attempt ceiling is the observable failure mode.                                     |
| Architecture          | The bound does not require a specific internal layering topology.                                                       |
| Specification / model | Initial-call counting and stop-before-extra-call ordering are normative technical semantics.                            |

No blocking mutation threshold is selected.

(verification-profile-req-structured-output-repair)=

## Profile · REQ_STRUCTURED_OUTPUT_REPAIR

**Verification intent.** Prove through the public structured-output path that one
schema-invalid provider response may be repaired into a validated result. Attempt
counting and prompt-space limits remain independently owned by child Technical
requirements.

**Models:** {ref}`Structured-output recovery <test-plan-structured-recovery-model>`

### Required coverage

| Test level         | Boundary   | Representation | M&S target |          Target |
| ------------------ | ---------- | -------------- | ---------- | --------------: |
| System Integration | Substitute | Surrogate      | L0         | **1 criterion** |

**Coverage basis.** One public recovery path must prove invalid first output, one repair
turn, validated final output, and the exact two-response interaction count.

**Representation basis.** Actual router, provider-adapter, schema-validation, and repair
logic runs against a scripted provider participant; the external participant is
Surrogate at L0.

### Verification criteria

| Criterion                       | Contract                                      | Test level         | Boundary   | Required paths | Success criterion                                                                                                       |
| ------------------------------- | --------------------------------------------- | ------------------ | ---------- | -------------: | ----------------------------------------------------------------------------------------------------------------------- |
| `VC_STRUCTURED_REPAIR_RECOVERY` | {need}`[[id]] <REQ_STRUCTURED_OUTPUT_REPAIR>` | System Integration | Substitute |              1 | With total attempt budget 2, an invalid first response followed by valid output succeeds on the final allowed response. |

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

| Technical requirement                                                                         | Target |
| --------------------------------------------------------------------------------------------- | ------ |
| {need}`Structured-output attempt counting is bounded <TREQ_STRUCTURED_OUTPUT_ATTEMPT_BOUNDS>` | PASS   |
| {need}`Repair prompts remain bounded <TREQ_REPAIR_PROMPT_BOUNDS>`                             | PASS   |

### Fault applicability

| REQUIRED                                                                     | OPTIONAL | N/A                                                                                                                                                                                |
| ---------------------------------------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `interface.payload-schema` · `spec.wrong-outcome` · `spec.missing-partition` | —        | `impl.comparison` · `impl.boundary` · `impl.control-flow` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.error-status` |
| —                                                                            | —        | `interface.unexpected-interaction` · `architecture.forbidden-edge` · `architecture.layer-bypass` · `spec.wrong-ordering-boundary`                                                  |

#### Fault-group rationale

| Group                 | Why                                                                                                                            |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| Implementation        | Attempt counting and prompt bounding are delegated to the child Technical requirements.                                        |
| Runtime / dependency  | Transport recovery is a separate provider-retry capability and is tested only when capabilities compose at Goal level.         |
| Interface / protocol  | A schema-invalid successful provider response is the public recovery stimulus.                                                 |
| Architecture          | The parent requirement does not prescribe internal layering.                                                                   |
| Specification / model | Invalid→repair→validated-result behavior is the normative product claim; missing the invalid partition would hide the feature. |

No blocking mutation threshold is selected.

(verification-profile-treq-structured-output-attempt-bounds)=

## Profile · TREQ_STRUCTURED_OUTPUT_ATTEMPT_BOUNDS

**Verification intent.** Prove that the configured structured-output maximum-attempt
count caps total provider responses evaluated, including the initial response and every
repair turn.

**Models:** {ref}`Structured-output recovery <test-plan-structured-recovery-model>`

### Required coverage

| Test level         | Boundary   | Representation | M&S target |          Target |
| ------------------ | ---------- | -------------- | ---------- | --------------: |
| System Integration | Substitute | Surrogate      | L0         | **1 criterion** |

**Coverage basis.** The minimum valid budget of one and an intermediate budget of two
form independent off-by-one boundaries. Both must prove exact provider-response counts.

**Representation basis.** Actual structured-output validation and repair-loop code runs
against a scripted provider participant; the external participant is Surrogate at L0.

### Verification criteria

| Criterion                            | Contract                                               | Test level         | Boundary   | Required paths | Required path IDs       | Success criterion                                                                                                    |
| ------------------------------------ | ------------------------------------------------------ | ------------------ | ---------- | -------------: | ----------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `VC_STRUCTURED_REPAIR_ATTEMPT_BOUND` | {need}`[[id]] <TREQ_STRUCTURED_OUTPUT_ATTEMPT_BOUNDS>` | System Integration | Substitute |              2 | `budget-1` · `budget-2` | Budgets 1 and 2 each stop after exactly that many invalid provider responses and expose the public structured error. |

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

| REQUIRED                                                                                       | OPTIONAL | N/A                                                                                                                    |
| ---------------------------------------------------------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------- |
| `impl.comparison` · `impl.boundary` · `impl.control-flow` · `interface.unexpected-interaction` | —        | `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.error-status` |
| `spec.wrong-outcome` · `spec.wrong-ordering-boundary`                                          | —        | `interface.payload-schema` · `architecture.forbidden-edge` · `architecture.layer-bypass` · `spec.missing-partition`    |

#### Fault-group rationale

| Group                 | Why                                                                                                     |
| --------------------- | ------------------------------------------------------------------------------------------------------- |
| Implementation        | Attempt-count comparison, boundary handling, and repair-loop control flow directly implement the cap.   |
| Runtime / dependency  | Transport failures are owned by provider retry; this Technical requirement counts structured responses. |
| Interface / protocol  | Any provider response evaluated after the configured total-attempt budget is an unexpected interaction. |
| Architecture          | The count bound does not prescribe a particular internal module topology.                               |
| Specification / model | The initial response is part of the budget, and exhaustion must occur before an extra repair turn.      |

No blocking mutation threshold is selected.

(verification-profile-treq-repair-prompt-bounds)=

## Profile · TREQ_REPAIR_PROMPT_BOUNDS

**Verification intent.** Prove that every dynamic component incorporated into a repair
prompt remains bounded independently of caller/provider-controlled input size.

**Models:** {ref}`Structured-output recovery <test-plan-structured-recovery-model>`

### Required coverage

| Test level | Boundary | Representation | M&S target |          Target |
| ---------- | -------- | -------------- | ---------- | --------------: |
| Component  | Local    | Actual         | —          | **1 criterion** |

**Coverage basis.** One property-based criterion spans every dynamic repair-prompt
component named by the Technical requirement and generates values beyond each configured
preview/cap boundary.

**Representation basis.** The actual local repair-prompt builder is exercised directly
with generated values; no external participant or model substitute is involved.

### Verification criteria

| Criterion                 | Contract                                   | Test level | Boundary | Required paths | Success criterion                                                                                                         |
| ------------------------- | ------------------------------------------ | ---------- | -------- | -------------: | ------------------------------------------------------------------------------------------------------------------------- |
| `VC_REPAIR_PROMPT_BOUNDS` | {need}`[[id]] <TREQ_REPAIR_PROMPT_BOUNDS>` | Component  | Local    |              1 | Property-generated schema identity, invalid output, and validation detail cannot expand the repair prompt beyond its cap. |

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

| REQUIRED                                                     | OPTIONAL | N/A                                                                                                                                                                     |
| ------------------------------------------------------------ | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `impl.boundary` · `impl.control-flow` · `spec.wrong-outcome` | —        | `impl.comparison` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.error-status` · `interface.payload-schema` |
| `spec.missing-partition`                                     | —        | `interface.unexpected-interaction` · `architecture.forbidden-edge` · `architecture.layer-bypass` · `spec.wrong-ordering-boundary`                                       |

#### Fault-group rationale

| Group                 | Why                                                                                                                         |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| Implementation        | Truncation/capping branches and per-component limits enforce bounded prompt growth.                                         |
| Runtime / dependency  | Prompt construction is local and has no external runtime dependency.                                                        |
| Interface / protocol  | The prompt builder consumes already-normalized dynamic values rather than owning an external protocol boundary.             |
| Architecture          | Bounded prompt construction does not prescribe module topology.                                                             |
| Specification / model | Schema identity, preview, invalid output, and validation detail are independent dynamic partitions that all require bounds. |

No blocking mutation threshold is selected.
