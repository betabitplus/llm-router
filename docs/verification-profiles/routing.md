(verification-profiles-routing)=

# Verification profiles · Routing reliability

These profiles own verification design for the parent contracts in
{need}`GOAL_ROUTING_RELIABILITY`. Product semantics remain in the normative
Requirements and Technical requirements. Targets below are derived from the routing
contracts and public policy semantics, not from the set of tests that already happens
to exist.

(verification-profile-req-sync-route-fallback)=

## Profile · REQ_SYNC_ROUTE_FALLBACK

**Verification intent.** Prove that a synchronous provider-route failure does not
terminate a request while another eligible route remains, and that the public result
retains the ordered failed/successful attempt trace.

**Models:** {ref}`Routing fallback <test-plan-routing-fallback-model>`

### Required coverage

| Test level         | Boundary   | Representation | M&S target |          Target |
| ------------------ | ---------- | -------------- | ---------- | --------------: |
| System Integration | Substitute | Surrogate      | L0         | **1 criterion** |

**Coverage basis.** One public synchronous workflow must execute a real provider-facing
attempt that fails, continue to the next eligible route, succeed there, and retain both
attempts in order. Additional failure mechanisms belong to the Fault Model rather than
inflating the semantic-path denominator.

**Representation basis.** The router/provider-adapter path is actual llm-router code.
A scripted external provider is sufficient because the claim is fallback control flow
and trace ordering, not fidelity of provider reasoning.

### Verification criteria

| Criterion                | Contract                                 | Test level         | Boundary   | Required paths | Success criterion                                                                                                                                  |
| ------------------------ | ---------------------------------------- | ------------------ | ---------- | -------------: | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `VC_SYNC_ROUTE_FALLBACK` | {need}`[[id]] <REQ_SYNC_ROUTE_FALLBACK>` | System Integration | Substitute |              1 | A failed synchronous provider attempt falls through to the next eligible route, which succeeds, and the trace preserves failed → successful order. |

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

| REQUIRED                                                                              | OPTIONAL | N/A                                                                                      |
| ------------------------------------------------------------------------------------- | -------- | ---------------------------------------------------------------------------------------- |
| `impl.control-flow` · `runtime.unavailable-disconnect` · `runtime.malformed-response` | —        | `impl.comparison` · `impl.boundary` · `runtime.latency-timeout`                          |
| `interface.unexpected-interaction` · `interface.error-status`                         | —        | `interface.payload-schema` · `architecture.forbidden-edge` · `architecture.layer-bypass` |
| `spec.wrong-outcome` · `spec.missing-partition` · `spec.wrong-ordering-boundary`      | —        | —                                                                                        |

#### Fault-group rationale

| Group                 | Why                                                                                                                                                              |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Implementation        | Fallback is a control-flow obligation; numeric thresholds are owned by the timeout/attempt-limit contracts.                                                      |
| Runtime / dependency  | Disconnect/unavailability and malformed provider results are distinct route-failure mechanisms that must still permit fallback; timeout is specified separately. |
| Interface / protocol  | A provider error status must not stop eligible fallback, and no additional external route may run after the successful fallback result.                          |
| Architecture          | This Requirement constrains observable routing behavior rather than a particular internal layering topology.                                                     |
| Specification / model | Successful fallback, failure-mechanism partitions, and failed→successful trace order are all normative semantics.                                                |

No blocking mutation threshold is selected; the required deterministic fault classes remain blocking.

(verification-profile-req-route-timeout-fallback)=

## Profile · REQ_ROUTE_TIMEOUT_FALLBACK

**Verification intent.** Prove the attempt-timeout boundary in both public execution
modes. Timeout must release the current wait and continue when an alternative route
exists, while the same timeout becomes the public terminal error when no alternative
exists.

**Models:** {ref}`Routing fallback <test-plan-routing-fallback-model>`

### Required coverage

| Test level         | Boundary   | Representation | M&S target |         Target |
| ------------------ | ---------- | -------------- | ---------- | -------------: |
| System Integration | Substitute | Surrogate      | L0         | **2 criteria** |

**Coverage basis.** Timeout has two independent outcome partitions — fallback remains
available versus terminal route — and both must hold for synchronous and asynchronous
public execution. Each criterion therefore requires two retained paths.

**Representation basis.** A deterministic delayed provider substitute is appropriate:
the claim is router timeout/fallback control flow and elapsed-attempt boundary, not
external provider fidelity.

### Verification criteria

| Criterion                   | Contract                                    | Test level         | Boundary   | Required paths | Success criterion                                                                                                     |
| --------------------------- | ------------------------------------------- | ------------------ | ---------- | -------------: | --------------------------------------------------------------------------------------------------------------------- |
| `VC_ROUTE_TIMEOUT_FALLBACK` | {need}`[[id]] <REQ_ROUTE_TIMEOUT_FALLBACK>` | System Integration | Substitute |              2 | Sync and async requests both stop waiting on a timed-out route, then continue to another eligible route and succeed.  |
| `VC_ROUTE_TIMEOUT_TERMINAL` | {need}`[[id]] <REQ_ROUTE_TIMEOUT_FALLBACK>` | System Integration | Substitute |              2 | Sync and async requests with no fallback both expose the public timeout after exactly the terminal timed-out attempt. |

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

| REQUIRED                                                                                                              | OPTIONAL | N/A                                                                                                                 |
| --------------------------------------------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------- |
| `impl.boundary` · `impl.control-flow` · `runtime.latency-timeout`                                                     | —        | `impl.comparison` · `runtime.unavailable-disconnect` · `runtime.malformed-response`                                 |
| `interface.unexpected-interaction` · `spec.wrong-outcome` · `spec.missing-partition` · `spec.wrong-ordering-boundary` | —        | `interface.error-status` · `interface.payload-schema` · `architecture.forbidden-edge` · `architecture.layer-bypass` |

#### Fault-group rationale

| Group                 | Why                                                                                                                                            |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| Implementation        | The configured timeout boundary and branch from timeout to fallback/terminal outcome are the implementation mechanisms under test.             |
| Runtime / dependency  | Delayed dependency behavior is the defining runtime fault; disconnect and malformed-response behavior belong to the generic fallback contract. |
| Interface / protocol  | Timeout must not create an extra route interaction beyond the declared fallback/terminal topology.                                             |
| Architecture          | The contract does not prescribe a particular timeout implementation layer.                                                                     |
| Specification / model | Fallback-vs-terminal and sync-vs-async partitions plus timeout-before-next-attempt ordering are normative.                                     |

No blocking mutation threshold is selected; the required deterministic fault classes remain blocking.

(verification-profile-req-route-attempt-limit)=

## Profile · REQ_ROUTE_ATTEMPT_LIMIT

**Verification intent.** Prove that route-attempt capping is correct at its minimum
boundary and for a partial candidate set, then prove through the public provider
boundary that a route beyond the configured cap is never attempted.

**Models:** {ref}`Routing fallback <test-plan-routing-fallback-model>`

### Required coverage

| Test level         | Boundary   | Representation | M&S target |          Target |
| ------------------ | ---------- | -------------- | ---------- | --------------: |
| Component          | Local      | Actual         | —          | **1 criterion** |
| System Integration | Substitute | Surrogate      | L0         | **1 criterion** |

**Coverage basis.** Component coverage owns boundary-value semantics for the smallest
valid cap and an intermediate cap smaller than the candidate set. System-integration
coverage proves the cap at the public provider boundary by making a route beyond the
limit observable and asserting that it is not called.

**Representation basis.** Ordering/capping is actual local code. The public path uses a
scripted provider only to observe the number of external route attempts, so Surrogate/L0
is sufficient.

### Verification criteria

| Criterion                           | Contract                                 | Test level         | Boundary   | Required paths | Success criterion                                                                                                          |
| ----------------------------------- | ---------------------------------------- | ------------------ | ---------- | -------------: | -------------------------------------------------------------------------------------------------------------------------- |
| `VC_ROUTE_ATTEMPT_LIMIT_BOUNDARIES` | {need}`[[id]] <REQ_ROUTE_ATTEMPT_LIMIT>` | Component          | Local      |              2 | A cap of 1 returns one candidate and an intermediate cap truncates a larger candidate set at exactly the configured count. |
| `VC_ROUTE_ATTEMPT_LIMIT_PUBLIC_CAP` | {need}`[[id]] <REQ_ROUTE_ATTEMPT_LIMIT>` | System Integration | Substitute |              1 | A public request with more failing routes than the configured cap performs no external interaction beyond that cap.        |

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

| REQUIRED                                                                             | OPTIONAL | N/A                                                                                                                                                  |
| ------------------------------------------------------------------------------------ | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `impl.comparison` · `impl.boundary` · `impl.control-flow`                            | —        | `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response`                                                          |
| `interface.unexpected-interaction` · `spec.wrong-outcome` · `spec.missing-partition` | —        | `interface.error-status` · `interface.payload-schema` · `architecture.forbidden-edge` · `architecture.layer-bypass` · `spec.wrong-ordering-boundary` |

#### Fault-group rationale

| Group                 | Why                                                                                                                             |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| Implementation        | The contract is a numeric boundary implemented by truncation/comparison/control-flow decisions.                                 |
| Runtime / dependency  | Provider failure is useful to expose multiple attempts, but dependency failure modes do not define the cap itself.              |
| Interface / protocol  | Any provider request beyond the configured limit is directly forbidden by the contract.                                         |
| Architecture          | No internal layering topology is part of the route-attempt-count claim.                                                         |
| Specification / model | Minimum/intermediate limit partitions and the observable capped outcome are normative; route ordering itself belongs elsewhere. |

No blocking mutation threshold is selected; the required deterministic fault classes remain blocking.

(verification-profile-req-route-sticky-start)=

## Profile · REQ_ROUTE_STICKY_START

**Verification intent.** Prove that route identity survives round-robin rotation,
fallback shuffling, and attempt capping, then prove that a real multi-hop fallback
updates the next public request to start from the route that actually succeeded.

**Models:** {ref}`Routing fallback <test-plan-routing-fallback-model>`

### Required coverage

| Test level         | Boundary   | Representation | M&S target |          Target |
| ------------------ | ---------- | -------------- | ---------- | --------------: |
| Component          | Local      | Actual         | —          |  **3 criteria** |
| System Integration | Substitute | Surrogate      | L0         | **1 criterion** |

**Coverage basis.** The derived route-order contract owns three independent ordering
invariants: round-robin rotation without reindexing, fallback shuffle preserving the
selected start, and an explicit successful-start identity surviving shuffle plus
attempt capping. The parent public criterion uses at least three routes so a
request-index increment cannot accidentally imitate sticky behavior.

**Representation basis.** Route ordering executes actual local code. The public
multi-hop workflow uses a deterministic provider substitute because the claim is
which configured route is contacted first, not provider fidelity.

### Verification criteria

| Criterion                               | Contract                                | Test level         | Boundary   | Required paths | Success criterion                                                                                                              |
| --------------------------------------- | --------------------------------------- | ------------------ | ---------- | -------------: | ------------------------------------------------------------------------------------------------------------------------------ |
| `VC_ROUTE_ORDER_ROUND_ROBIN_IDENTITY`   | {need}`[[id]] <TREQ_ROUTE_ORDER>`       | Component          | Local      |              1 | Round-robin rotation changes attempt order without changing stable route identities.                                           |
| `VC_ROUTE_ORDER_SHUFFLE_START_IDENTITY` | {need}`[[id]] <TREQ_ROUTE_ORDER>`       | Component          | Local      |              1 | Fallback shuffling never moves the already selected starting route away from the first attempt.                                |
| `VC_ROUTE_ORDER_STICKY_START_IDENTITY`  | {need}`[[id]] <TREQ_ROUTE_ORDER>`       | Component          | Local      |              1 | An explicit successful starting-route identity remains first after fallback shuffle and attempt capping.                       |
| `VC_ROUTE_STICKY_MULTI_HOP`             | {need}`[[id]] <REQ_ROUTE_STICKY_START>` | System Integration | Substitute |              1 | After two failed routes and success on a third, the next request starts on that third route with no earlier-route interaction. |

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

| REQUIRED                                                                         | OPTIONAL | N/A                                                                                                                 |
| -------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------- |
| `impl.comparison` · `impl.control-flow` · `interface.unexpected-interaction`     | —        | `impl.boundary` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response`       |
| `spec.wrong-outcome` · `spec.missing-partition` · `spec.wrong-ordering-boundary` | —        | `interface.error-status` · `interface.payload-schema` · `architecture.forbidden-edge` · `architecture.layer-bypass` |

#### Fault-group rationale

| Group                 | Why                                                                                                                                               |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| Implementation        | Stable identity lookup and control flow determine whether the actual successful route is selected next.                                           |
| Runtime / dependency  | The provider failure that creates fallback is setup; dependency failure types are covered by fallback/timeout contracts rather than sticky state. |
| Interface / protocol  | Calling an earlier route before the most recently successful route on the next request is an explicitly forbidden interaction.                    |
| Architecture          | Sticky state does not require a particular internal layering topology.                                                                            |
| Specification / model | Multi-hop state, selected-route identity, and before/after request ordering are the essence of this Requirement.                                  |

No blocking mutation threshold is selected; the required deterministic fault classes remain blocking.

(verification-profile-req-rate-limit-routing)=

## Profile · REQ_RATE_LIMIT_ROUTING

**Verification intent.** Prove limiter state semantics independently of provider
behavior, then prove public routing decisions: skip blocked candidates, obey the
all-blocked fail/wait policy, choose the earliest availability when waiting, and use
available automatic credentials before waiting on a blocked one.

**Models:** {ref}`Rate-limit-aware routing <test-plan-rate-limit-routing-model>`

### Required coverage

| Test level         | Boundary   | Representation | M&S target |         Target |
| ------------------ | ---------- | -------------- | ---------- | -------------: |
| Component          | Local      | Actual         | —          | **4 criteria** |
| System Integration | Substitute | Surrogate      | L0         | **5 criteria** |

**Coverage basis.** Component coverage owns state partitioning: provider/key isolation,
both RPS-vs-RPM conservative interval directions, success reset, and cooldown threshold
behavior. System-integration coverage owns observable routing decisions and uses a
controlled provider boundary so no external service timing is needed to decide whether a
candidate should be skipped, waited for, or selected.

**Representation basis.** Limiter state is actual local code. Public workflows execute
actual router/provider-adapter code against a scripted provider substitute; Surrogate/L0
is sufficient because the claim is local availability policy and external interaction
ordering.

### Verification criteria

| Criterion                                 | Contract                                                | Test level         | Boundary   | Required paths | Success criterion                                                                                                          |
| ----------------------------------------- | ------------------------------------------------------- | ------------------ | ---------- | -------------: | -------------------------------------------------------------------------------------------------------------------------- |
| `VC_RATE_LIMIT_PROVIDER_KEY_ISOLATION`    | {need}`[[id]] <TREQ_RATE_LIMIT_STATE>`                  | Component          | Local      |              2 | State in one provider/key bucket does not block another key of that provider or the same key ID under another provider.    |
| `VC_RATE_LIMIT_CONSERVATIVE_INTERVAL`     | {need}`[[id]] <TREQ_RATE_LIMIT_STATE>`                  | Component          | Local      |              2 | The limiter uses the longer spacing interval in both RPS-dominant and RPM-dominant configurations.                         |
| `VC_RATE_LIMIT_SUCCESS_RESET`             | {need}`[[id]] <TREQ_RATE_LIMIT_STATE>`                  | Component          | Local      |              1 | A success clears transient failure count so a later failure sequence must reach the configured threshold again.            |
| `VC_RATE_LIMIT_COOLDOWN_THRESHOLD`        | {need}`[[id]] <TREQ_RATE_LIMIT_COOLDOWN_POLICY>`        | Component          | Local      |              2 | Below-threshold failures do not block the bucket, while the threshold failure blocks it for the configured cooldown.       |
| `VC_RATE_LIMIT_SKIP_BLOCKED_ROUTE`        | {need}`[[id]] <REQ_RATE_LIMIT_ROUTING>`                 | System Integration | Substitute |              1 | A blocked preferred route is not called when another eligible route is immediately available.                              |
| `VC_RATE_LIMIT_ALL_BLOCKED_FAIL_FAST`     | {need}`[[id]] <REQ_RATE_LIMIT_ROUTING>`                 | System Integration | Substitute |              1 | When every candidate is blocked and waiting is disabled, the public request fails without sleeping or calling a provider.  |
| `VC_RATE_LIMIT_ALL_BLOCKED_WAIT_EARLIEST` | {need}`[[id]] <TREQ_RATE_LIMIT_AVAILABILITY_SELECTION>` | System Integration | Substitute |              1 | When waiting is enabled and every candidate is blocked, the candidate with the shortest remaining wait is executed first.  |
| `VC_RATE_LIMIT_AVAILABLE_KEY_BEFORE_WAIT` | {need}`[[id]] <TREQ_RATE_LIMIT_AVAILABILITY_SELECTION>` | System Integration | Substitute |              1 | Automatic key selection uses an unblocked credential instead of waiting on the next rotating key when that key is blocked. |
| `VC_RATE_LIMIT_AUTO_KEY_ROTATION`         | {need}`[[id]] <REQ_RATE_LIMIT_ROUTING>`                 | System Integration | Substitute |              1 | With two available automatic credentials, consecutive requests rotate across them before reuse requires waiting.           |

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

| REQUIRED                                                                                                                  | OPTIONAL                         | N/A                                                                                   |
| ------------------------------------------------------------------------------------------------------------------------- | -------------------------------- | ------------------------------------------------------------------------------------- |
| `impl.comparison` · `impl.boundary` · `impl.control-flow` · `interface.unexpected-interaction` · `interface.error-status` | `runtime.unavailable-disconnect` | `runtime.latency-timeout` · `runtime.malformed-response` · `interface.payload-schema` |
| `architecture.layer-bypass` · `spec.wrong-outcome` · `spec.missing-partition` · `spec.wrong-ordering-boundary`            | —                                | `architecture.forbidden-edge`                                                         |

#### Fault-group rationale

| Group                 | Why                                                                                                                                                         |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Implementation        | Limiter thresholds, wait comparisons, candidate choice, and branch decisions are the implementation mechanisms that enforce availability policy.            |
| Runtime / dependency  | Transport unavailability is useful non-blocking evidence for failure-driven cooldown; provider latency and malformed payloads are owned by other contracts. |
| Interface / protocol  | A blocked route/key must not be contacted while an unblocked alternative exists, and provider error status is a concrete failure source for cooldown.       |
| Architecture          | Availability-aware auto-key selection must consult limiter state; bypassing that boundary recreates avoidable waiting even when another key is free.        |
| Specification / model | Provider/key partitions, wait/fail policy, earliest-availability ordering, and available-before-blocked selection are all normative.                        |

No parent-level blocking mutation threshold is selected. The retained Test Strength for
{need}`TREQ_RATE_LIMIT_STATE` remains diagnostic under the project Test Plan; required
fault classes above are still blocking.
