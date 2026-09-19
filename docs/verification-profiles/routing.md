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

| Criterion                   | Contract                                    | Test level         | Boundary   | Required paths | Required path IDs | Success criterion                                                                                                     |
| --------------------------- | ------------------------------------------- | ------------------ | ---------- | -------------: | ----------------- | --------------------------------------------------------------------------------------------------------------------- |
| `VC_ROUTE_TIMEOUT_FALLBACK` | {need}`[[id]] <REQ_ROUTE_TIMEOUT_FALLBACK>` | System Integration | Substitute |              2 | `sync` · `async`  | Sync and async requests both stop waiting on a timed-out route, then continue to another eligible route and succeed.  |
| `VC_ROUTE_TIMEOUT_TERMINAL` | {need}`[[id]] <REQ_ROUTE_TIMEOUT_FALLBACK>` | System Integration | Substitute |              2 | `sync` · `async`  | Sync and async requests with no fallback both expose the public timeout after exactly the terminal timed-out attempt. |

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

| Criterion                           | Contract                                 | Test level         | Boundary   | Required paths | Required path IDs                  | Success criterion                                                                                                          |
| ----------------------------------- | ---------------------------------------- | ------------------ | ---------- | -------------: | ---------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| `VC_ROUTE_ATTEMPT_LIMIT_BOUNDARIES` | {need}`[[id]] <REQ_ROUTE_ATTEMPT_LIMIT>` | Component          | Local      |              2 | `minimum-cap` · `intermediate-cap` | A cap of 1 returns one candidate and an intermediate cap truncates a larger candidate set at exactly the configured count. |
| `VC_ROUTE_ATTEMPT_LIMIT_PUBLIC_CAP` | {need}`[[id]] <REQ_ROUTE_ATTEMPT_LIMIT>` | System Integration | Substitute |              1 | —                                  | A public request with more failing routes than the configured cap performs no external interaction beyond that cap.        |

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

**Verification intent.** Prove the public contract directly: after fallback succeeds, the
next request through the same router begins from the route that actually succeeded.
Internal route-order invariants are owned by {need}`TREQ_ROUTE_ORDER`.

**Models:** {ref}`Routing fallback <test-plan-routing-fallback-model>`

### Required coverage

| Test level         | Boundary | Representation | M&S target |          Target |
| ------------------ | -------- | -------------- | ---------- | --------------: |
| System Integration | Replay   | Surrogate      | L0         | **1 criterion** |

**Coverage basis.** The Requirement has one direct observable obligation: a subsequent
request starts from the previously successful route. Multi-hop interaction across fallback
and sticky-start contracts is owned by Feature-level Capability integration instead of
being counted again as direct Requirement evidence.

**Representation basis.** The retained public workflow executes the real router/runtime
against a VCR replay of a previously recorded provider interaction. The replay is therefore
Surrogate/L0 evidence for the public routing-order claim.

### Verification criteria

| Criterion                           | Contract                                | Test level         | Boundary | Required paths | Success criterion                                                                                   |
| ----------------------------------- | --------------------------------------- | ------------------ | -------- | -------------: | --------------------------------------------------------------------------------------------------- |
| `VC_ROUTE_STICKY_PUBLIC_NEXT_START` | {need}`[[id]] <REQ_ROUTE_STICKY_START>` | System Integration | Replay   |              1 | After fallback succeeds, the next request starts directly from the route that previously succeeded. |

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

| Technical requirement                            | Target |
| ------------------------------------------------ | ------ |
| {need}`Stable route ordering <TREQ_ROUTE_ORDER>` | PASS   |

### Fault applicability

| REQUIRED                                                                                   | OPTIONAL | N/A                                                                                                                                                                                                                                                                                                      |
| ------------------------------------------------------------------------------------------ | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `interface.unexpected-interaction` · `spec.wrong-outcome` · `spec.wrong-ordering-boundary` | —        | `impl.comparison` · `impl.boundary` · `impl.control-flow` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.error-status` · `interface.payload-schema` · `architecture.forbidden-edge` · `architecture.layer-bypass` · `spec.missing-partition` |

#### Fault-group rationale

| Group                 | Why                                                                                                                                                |
| --------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| Implementation        | Route-order implementation mechanics are owned by the derived technical contract rather than this public Requirement.                              |
| Runtime / dependency  | Dependency failure creates the fallback precondition; timeout/unavailability semantics are owned by their own routing contracts.                   |
| Interface / protocol  | Calling a route before the previously successful route is a directly forbidden public interaction.                                                 |
| Architecture          | No internal layering topology is normative for the public sticky-start outcome.                                                                    |
| Specification / model | The visible next-start outcome and before/after ordering define the Requirement; broader route-order partitions belong to the TREQ/Feature levels. |

No blocking mutation threshold is selected for the public Requirement.

(verification-profile-treq-route-order)=

## Profile · TREQ_ROUTE_ORDER

**Verification intent.** Prove the internal route-order invariants that preserve stable
route identity across rotation, shuffling, and selected-start handling.

**Models:** {ref}`Routing fallback <test-plan-routing-fallback-model>`

### Required coverage

| Test level | Boundary | Representation | M&S target |         Target |
| ---------- | -------- | -------------- | ---------- | -------------: |
| Component  | Local    | Actual         | —          | **3 criteria** |

**Coverage basis.** The technical contract owns three independent route-order invariants:
round-robin rotation preserves stable identities, fallback shuffling preserves the selected
start, and an explicit successful-start identity remains first through attempt capping.

**Representation basis.** The tests execute the actual local route-order implementation
without an external dependency or surrogate model.

### Verification criteria

| Criterion                               | Contract                          | Test level | Boundary | Required paths | Success criterion                                                                                        |
| --------------------------------------- | --------------------------------- | ---------- | -------- | -------------: | -------------------------------------------------------------------------------------------------------- |
| `VC_ROUTE_ORDER_ROUND_ROBIN_IDENTITY`   | {need}`[[id]] <TREQ_ROUTE_ORDER>` | Component  | Local    |              1 | Round-robin rotation changes attempt order without changing stable route identities.                     |
| `VC_ROUTE_ORDER_SHUFFLE_START_IDENTITY` | {need}`[[id]] <TREQ_ROUTE_ORDER>` | Component  | Local    |              1 | Fallback shuffling never moves the already selected starting route away from the first attempt.          |
| `VC_ROUTE_ORDER_STICKY_START_IDENTITY`  | {need}`[[id]] <TREQ_ROUTE_ORDER>` | Component  | Local    |              1 | An explicit successful starting-route identity remains first after fallback shuffle and attempt capping. |

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

| REQUIRED                                                                                            | OPTIONAL | N/A                                                                                                                                                                                                                                                                                             |
| --------------------------------------------------------------------------------------------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `impl.comparison` · `impl.control-flow` · `spec.missing-partition` · `spec.wrong-ordering-boundary` | —        | `impl.boundary` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.unexpected-interaction` · `interface.error-status` · `interface.payload-schema` · `architecture.forbidden-edge` · `architecture.layer-bypass` · `spec.wrong-outcome` |

#### Fault-group rationale

| Group                 | Why                                                                                                         |
| --------------------- | ----------------------------------------------------------------------------------------------------------- |
| Implementation        | Comparison and branch/order changes can move or lose the selected route identity.                           |
| Runtime / dependency  | No external runtime behavior is part of this local ordering invariant.                                      |
| Interface / protocol  | Provider interaction order is verified at the parent/Feature level, not by this local technical contract.   |
| Architecture          | Route ordering does not require a particular package-layer edge.                                            |
| Specification / model | Missing ordering partitions or wrong before/after ordering directly invalidate the technical invariant set. |

No blocking mutation threshold is selected; deterministic technical fault obligations remain blocking.

(verification-profile-req-rate-limit-routing)=

## Profile · REQ_RATE_LIMIT_ROUTING

**Verification intent.** Prove the directly observable routing contract: blocked candidates
are skipped, all-blocked no-wait policy fails immediately, and available automatic
credentials rotate before reuse requires waiting. Limiter-state, cooldown-threshold, and
availability-selection mechanisms are owned by their derived TREQ profiles.

**Models:** {ref}`Rate-limit-aware routing <test-plan-rate-limit-routing-model>`

### Required coverage

| Test level         | Boundary   | Representation | M&S target |         Target |
| ------------------ | ---------- | -------------- | ---------- | -------------: |
| System Integration | Substitute | Surrogate      | L0         | **3 criteria** |

**Coverage basis.** Direct Requirement coverage is limited to externally observable route
and key decisions. Technical state partitioning, threshold behavior, earliest-wait
selection, and blocked-key avoidance are verified by their respective TREQ profiles.

**Representation basis.** Public workflows execute actual router/provider-adapter code
against a scripted provider substitute. Surrogate/L0 is sufficient because the direct
Requirement claims local availability policy and externally visible interaction ordering.

### Verification criteria

| Criterion                             | Contract                                | Test level         | Boundary   | Required paths | Success criterion                                                                                                         |
| ------------------------------------- | --------------------------------------- | ------------------ | ---------- | -------------: | ------------------------------------------------------------------------------------------------------------------------- |
| `VC_RATE_LIMIT_SKIP_BLOCKED_ROUTE`    | {need}`[[id]] <REQ_RATE_LIMIT_ROUTING>` | System Integration | Substitute |              1 | A blocked preferred route is not called when another eligible route is immediately available.                             |
| `VC_RATE_LIMIT_ALL_BLOCKED_FAIL_FAST` | {need}`[[id]] <REQ_RATE_LIMIT_ROUTING>` | System Integration | Substitute |              1 | When every candidate is blocked and waiting is disabled, the public request fails without sleeping or calling a provider. |
| `VC_RATE_LIMIT_AUTO_KEY_ROTATION`     | {need}`[[id]] <REQ_RATE_LIMIT_ROUTING>` | System Integration | Substitute |              1 | With two available automatic credentials, consecutive requests rotate across them before reuse requires waiting.          |

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

| Technical requirement                                                                       | Target |
| ------------------------------------------------------------------------------------------- | ------ |
| {need}`Isolated limiter state <TREQ_RATE_LIMIT_STATE>`                                      | PASS   |
| {need}`Failure threshold opens a provider-key cooldown <TREQ_RATE_LIMIT_COOLDOWN_POLICY>`   | PASS   |
| {need}`Availability-aware route and key selection <TREQ_RATE_LIMIT_AVAILABILITY_SELECTION>` | PASS   |

### Fault applicability

| REQUIRED                                                                             | OPTIONAL                         | N/A                                                                                                                                                                                                                                                                         |
| ------------------------------------------------------------------------------------ | -------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `interface.unexpected-interaction` · `interface.error-status` · `spec.wrong-outcome` | `runtime.unavailable-disconnect` | `impl.comparison` · `impl.boundary` · `impl.control-flow` · `runtime.latency-timeout` · `runtime.malformed-response` · `interface.payload-schema` · `architecture.forbidden-edge` · `architecture.layer-bypass` · `spec.missing-partition` · `spec.wrong-ordering-boundary` |

#### Fault-group rationale

| Group                 | Why                                                                                                                                  |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| Implementation        | Internal limiter and selection mechanics are owned by the derived TREQ contracts.                                                    |
| Runtime / dependency  | Provider unavailability is a useful non-blocking challenge to public routing progress; other dependency classes are owned elsewhere. |
| Interface / protocol  | A blocked route must not be contacted and provider error status is a concrete public failure source.                                 |
| Architecture          | No internal layering edge is itself part of the direct public Requirement.                                                           |
| Specification / model | A wrong visible routing outcome invalidates the Requirement; detailed state/ordering partitions belong to TREQ profiles.             |

No blocking mutation threshold is selected for the public Requirement.

(verification-profile-treq-rate-limit-state)=

## Profile · TREQ_RATE_LIMIT_STATE

**Verification intent.** Prove provider/key isolation, conservative request spacing, and
success reset as local limiter-state invariants.

**Models:** {ref}`Rate-limit-aware routing <test-plan-rate-limit-routing-model>`

### Required coverage

| Test level | Boundary | Representation | M&S target |         Target |
| ---------- | -------- | -------------- | ---------- | -------------: |
| Component  | Local    | Actual         | —          | **3 criteria** |

**Coverage basis.** The technical contract owns three state invariants with explicit
provider/key and RPS/RPM partitions.

**Representation basis.** Unit tests execute the actual local limiter implementation;
there is no external model or provider boundary.

### Verification criteria

| Criterion                              | Contract                               | Test level | Boundary | Required paths | Required path IDs                                     | Success criterion                                                                                                       |
| -------------------------------------- | -------------------------------------- | ---------- | -------- | -------------: | ----------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `VC_RATE_LIMIT_PROVIDER_KEY_ISOLATION` | {need}`[[id]] <TREQ_RATE_LIMIT_STATE>` | Component  | Local    |              2 | `same-provider-other-key` · `same-key-other-provider` | State in one provider/key bucket does not block another key of that provider or the same key ID under another provider. |
| `VC_RATE_LIMIT_CONSERVATIVE_INTERVAL`  | {need}`[[id]] <TREQ_RATE_LIMIT_STATE>` | Component  | Local    |              2 | `rpm-dominant` · `rps-dominant`                       | The limiter uses the longer spacing interval in both RPS-dominant and RPM-dominant configurations.                      |
| `VC_RATE_LIMIT_SUCCESS_RESET`          | {need}`[[id]] <TREQ_RATE_LIMIT_STATE>` | Component  | Local    |              1 | —                                                     | A success clears transient failure count so a later failure sequence must reach the configured threshold again.         |

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

| REQUIRED                                                                             | OPTIONAL | N/A                                                                                                                                                                                                                                                                                                            |
| ------------------------------------------------------------------------------------ | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `impl.comparison` · `impl.boundary` · `impl.control-flow` · `spec.missing-partition` | —        | `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.unexpected-interaction` · `interface.error-status` · `interface.payload-schema` · `architecture.forbidden-edge` · `architecture.layer-bypass` · `spec.wrong-outcome` · `spec.wrong-ordering-boundary` |

#### Fault-group rationale

| Group                 | Why                                                                                                |
| --------------------- | -------------------------------------------------------------------------------------------------- |
| Implementation        | Comparisons, thresholds, and branch/reset logic directly implement the technical state invariants. |
| Runtime / dependency  | The invariants are local state behavior and do not depend on an external provider fault mode.      |
| Interface / protocol  | No external payload or interaction shape is normative for this TREQ.                               |
| Architecture          | No package-layer edge is part of the state invariant.                                              |
| Specification / model | Missing provider/key or interval partitions would leave part of the technical contract unproved.   |

No blocking mutation threshold is selected in this profile; retained class-wide mutation evidence is not attributed to this TREQ unless objective scope attribution becomes available.

(verification-profile-treq-rate-limit-cooldown-policy)=

## Profile · TREQ_RATE_LIMIT_COOLDOWN_POLICY

**Verification intent.** Prove the exact failure threshold and configured cooldown
transition for each provider/key limiter bucket.

**Models:** {ref}`Rate-limit-aware routing <test-plan-rate-limit-routing-model>`

### Required coverage

| Test level | Boundary | Representation | M&S target |          Target |
| ---------- | -------- | -------------- | ---------- | --------------: |
| Component  | Local    | Actual         | —          | **1 criterion** |

**Coverage basis.** Below-threshold and at-threshold cases form the required boundary
partition for the cooldown transition.

**Representation basis.** Unit tests execute the actual limiter implementation with a
controlled clock/state setup and no external dependency.

### Verification criteria

| Criterion                          | Contract                                         | Test level | Boundary | Required paths | Required path IDs                  | Success criterion                                                                                                    |
| ---------------------------------- | ------------------------------------------------ | ---------- | -------- | -------------: | ---------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `VC_RATE_LIMIT_COOLDOWN_THRESHOLD` | {need}`[[id]] <TREQ_RATE_LIMIT_COOLDOWN_POLICY>` | Component  | Local    |              2 | `below-threshold` · `at-threshold` | Below-threshold failures do not block the bucket, while the threshold failure blocks it for the configured cooldown. |

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

| REQUIRED                                                                         | OPTIONAL | N/A                                                                                                                                                                                                                                                                                                                |
| -------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `impl.comparison` · `impl.boundary` · `impl.control-flow` · `spec.wrong-outcome` | —        | `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.unexpected-interaction` · `interface.error-status` · `interface.payload-schema` · `architecture.forbidden-edge` · `architecture.layer-bypass` · `spec.missing-partition` · `spec.wrong-ordering-boundary` |

#### Fault-group rationale

| Group                 | Why                                                                                                   |
| --------------------- | ----------------------------------------------------------------------------------------------------- |
| Implementation        | Threshold comparisons and control flow directly determine the transition.                             |
| Runtime / dependency  | External provider behavior may cause failures but does not define the configured threshold semantics. |
| Interface / protocol  | No provider payload shape is part of this local TREQ.                                                 |
| Architecture          | No package-layer topology is normative for the cooldown rule.                                         |
| Specification / model | A wrong blocked/unblocked outcome at the threshold directly violates the policy.                      |

No blocking mutation threshold is selected; deterministic fault obligations remain blocking.

(verification-profile-treq-rate-limit-availability-selection)=

## Profile · TREQ_RATE_LIMIT_AVAILABILITY_SELECTION

**Verification intent.** Prove that availability ordering selects the earliest or
immediately usable route/key instead of waiting on a worse candidate.

**Models:** {ref}`Rate-limit-aware routing <test-plan-rate-limit-routing-model>`

### Required coverage

| Test level         | Boundary   | Representation | M&S target |         Target |
| ------------------ | ---------- | -------------- | ---------- | -------------: |
| System Integration | Substitute | Surrogate      | L0         | **2 criteria** |

**Coverage basis.** The technical selection policy has two externally observable
partitions: all candidates blocked with waiting enabled, and automatic-key selection with
one blocked key and one immediately available key.

**Representation basis.** The actual router/limiter path runs against a deterministic
provider substitute. Surrogate/L0 is sufficient because the claim is candidate
availability ordering, not provider semantic fidelity.

### Verification criteria

| Criterion                                 | Contract                                                | Test level         | Boundary   | Required paths | Success criterion                                                                                                          |
| ----------------------------------------- | ------------------------------------------------------- | ------------------ | ---------- | -------------: | -------------------------------------------------------------------------------------------------------------------------- |
| `VC_RATE_LIMIT_ALL_BLOCKED_WAIT_EARLIEST` | {need}`[[id]] <TREQ_RATE_LIMIT_AVAILABILITY_SELECTION>` | System Integration | Substitute |              1 | When waiting is enabled and every candidate is blocked, the candidate with the shortest remaining wait is executed first.  |
| `VC_RATE_LIMIT_AVAILABLE_KEY_BEFORE_WAIT` | {need}`[[id]] <TREQ_RATE_LIMIT_AVAILABILITY_SELECTION>` | System Integration | Substitute |              1 | Automatic key selection uses an unblocked credential instead of waiting on the next rotating key when that key is blocked. |

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

| REQUIRED                                                                                                                                    | OPTIONAL | N/A                                                                                                                                                                                                                                                     |
| ------------------------------------------------------------------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `impl.comparison` · `impl.control-flow` · `interface.unexpected-interaction` · `architecture.layer-bypass` · `spec.wrong-ordering-boundary` | —        | `impl.boundary` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.error-status` · `interface.payload-schema` · `architecture.forbidden-edge` · `spec.wrong-outcome` · `spec.missing-partition` |

#### Fault-group rationale

| Group                 | Why                                                                                                          |
| --------------------- | ------------------------------------------------------------------------------------------------------------ |
| Implementation        | Candidate comparisons and control flow choose which available route/key runs.                                |
| Runtime / dependency  | Provider transport failures are not the selection rule itself.                                               |
| Interface / protocol  | Contacting a blocked candidate while an immediately available alternative exists is a forbidden interaction. |
| Architecture          | Availability-aware selection must consult limiter state; bypassing that layer recreates avoidable waiting.   |
| Specification / model | Earliest-availability and available-before-wait ordering are the normative technical semantics.              |

No blocking mutation threshold is selected; deterministic fault obligations remain blocking.
