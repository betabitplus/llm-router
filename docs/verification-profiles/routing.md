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
terminate a request while another eligible route remains, that the public result
retains the ordered failed/successful attempt trace, and that a request whose every
route fails raises the last route's error.

**Models:** {ref}`Routing fallback <test-plan-routing-fallback-model>`

### Required coverage

| Test level         | Boundary   | Representation | M&S target |         Target |
| ------------------ | ---------- | -------------- | ---------- | -------------: |
| System Integration | Substitute | Surrogate      | L0         | **2 criteria** |

**Coverage basis.** One public synchronous workflow must execute a real provider-facing
attempt that fails, continue to the next eligible route, succeed there, and retain both
attempts in order. A second one fails on every eligible route and must raise the last
route's error. Additional failure mechanisms belong to the Fault Model rather than
inflating the semantic-path denominator.

**Representation basis.** The router/provider-adapter path is actual llm-router code.
A scripted external provider is sufficient because the claim is fallback control flow
and trace ordering, not fidelity of provider reasoning.

### Verification criteria

| Criterion                         | Contract                                 | Test level         | Boundary   | Required paths | Success criterion                                                                                                                                  |
| --------------------------------- | ---------------------------------------- | ------------------ | ---------- | -------------: | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `VC_SYNC_ROUTE_FALLBACK`          | {need}`[[id]] <REQ_SYNC_ROUTE_FALLBACK>` | System Integration | Substitute |              1 | A failed synchronous provider attempt falls through to the next eligible route, which succeeds, and the trace preserves failed → successful order. |
| `VC_SYNC_ROUTE_FALLBACK_TERMINAL` | {need}`[[id]] <REQ_SYNC_ROUTE_FALLBACK>` | System Integration | Substitute |              1 | When every eligible synchronous route fails, each is attempted once and the request raises the last route's provider error.                        |

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

| REQUIRED                                                                                              | OPTIONAL | N/A                                                                                      |
| ----------------------------------------------------------------------------------------------------- | -------- | ---------------------------------------------------------------------------------------- |
| `impl.control-flow` · `impl.effect` · `runtime.unavailable-disconnect` · `runtime.malformed-response` | —        | `impl.comparison` · `impl.boundary` · `impl.arithmetic` · `runtime.latency-timeout`      |
| `interface.unexpected-interaction` · `interface.error-status`                                         | —        | `interface.payload-schema` · `architecture.forbidden-edge` · `architecture.layer-bypass` |
| `spec.wrong-outcome` · `spec.missing-partition` · `spec.wrong-ordering-boundary`                      | —        | —                                                                                        |

#### Fault-group rationale

| Group                 | Why                                                                                                                                                                                |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Implementation        | Fallback is a control-flow obligation; numeric thresholds are owned by the timeout/attempt-limit contracts. A dropped attempt record or terminal raise loses the fallback outcome. |
| Runtime / dependency  | Disconnect/unavailability and malformed provider results are distinct route-failure mechanisms that must still permit fallback; timeout is specified separately.                   |
| Interface / protocol  | A provider error status must not stop eligible fallback, and no additional external route may run after the successful fallback result.                                            |
| Architecture          | This Requirement constrains observable routing behavior rather than a particular internal layering topology.                                                                       |
| Specification / model | Successful fallback, failure-mechanism partitions, failed→successful trace order, and the last route's error when every route fails are all normative semantics.                   |

### Semantic mutants

| Fault class                        | Target                                                                | Budget | Risk                                                                                      |
| ---------------------------------- | --------------------------------------------------------------------- | -----: | ----------------------------------------------------------------------------------------- |
| `spec.wrong-outcome`               | `src/llm_router/_internal/runtime/router.py::RouterRuntime._run_sync` |      2 | a result its requirement or criteria name is computed or chosen wrongly                   |
| `spec.missing-partition`           | `src/llm_router/_internal/runtime/router.py::RouterRuntime._run_sync` |      2 | one input partition its requirement or criteria name is no longer handled as they say     |
| `spec.wrong-ordering-boundary`     | `src/llm_router/_internal/runtime/router.py::RouterRuntime._run_sync` |      2 | an order or a before/after boundary its requirement names is broken                       |
| `interface.unexpected-interaction` | `src/llm_router/_internal/runtime/router.py::RouterRuntime._run_sync` |      2 | an external interaction its requirement rules out happens anyway                          |
| `interface.error-status`           | `src/llm_router/_internal/runtime/router.py::RouterRuntime._run_sync` |      2 | an error the interface must report comes out with the wrong type or status, or not at all |

Chosen by the default selection (050): every `spec.*` and `interface.*` class this profile
requires, at each function of the contract's `@impl` scope. Rule operators change operators and
statements; they cannot change what the requirement means.

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

### Required technical support

| Technical requirement                                                                  | Target |
| -------------------------------------------------------------------------------------- | ------ |
| {need}`A timed-out attempt starts no further work <TREQ_TIMED_OUT_ATTEMPT_STOPS>`      | PASS   |
| {need}`A timed attempt keeps the caller's context <TREQ_ATTEMPT_KEEPS_CALLER_CONTEXT>` | PASS   |

### Fault applicability

| REQUIRED                                                                                                              | OPTIONAL | N/A                                                                                                                       |
| --------------------------------------------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------- |
| `impl.control-flow` · `impl.effect` · `runtime.latency-timeout`                                                       | —        | `impl.comparison` · `impl.boundary` · `impl.arithmetic` · `runtime.unavailable-disconnect` · `runtime.malformed-response` |
| `interface.unexpected-interaction` · `spec.wrong-outcome` · `spec.missing-partition` · `spec.wrong-ordering-boundary` | —        | `interface.error-status` · `interface.payload-schema` · `architecture.forbidden-edge` · `architecture.layer-bypass`       |

#### Fault-group rationale

| Group                 | Why                                                                                                                                                                                                                                                                                                                                                 |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Implementation        | The configured timeout boundary and branch from timeout to fallback/terminal outcome are the implementation mechanisms under test. A dropped timeout raise or attempt record changes the outcome. The attempt's time limit is enforced by `Future.result(timeout=…)` and the router compares no time of its own, so `impl.boundary` does not apply. |
| Runtime / dependency  | Delayed dependency behavior is the defining runtime fault; disconnect and malformed-response behavior belong to the generic fallback contract.                                                                                                                                                                                                      |
| Interface / protocol  | Timeout must not create an extra route interaction beyond the declared fallback/terminal topology.                                                                                                                                                                                                                                                  |
| Architecture          | The contract does not prescribe a particular timeout implementation layer.                                                                                                                                                                                                                                                                          |
| Specification / model | Fallback-vs-terminal and sync-vs-async partitions plus timeout-before-next-attempt ordering are normative.                                                                                                                                                                                                                                          |

### Semantic mutants

| Fault class                        | Target                                                                              | Budget | Risk                                                                                  |
| ---------------------------------- | ----------------------------------------------------------------------------------- | -----: | ------------------------------------------------------------------------------------- |
| `spec.wrong-outcome`               | `src/llm_router/_internal/runtime/router.py::RouterRuntime._call_sync_with_timeout` |      2 | a result its requirement or criteria name is computed or chosen wrongly               |
| `spec.missing-partition`           | `src/llm_router/_internal/runtime/router.py::RouterRuntime._call_sync_with_timeout` |      2 | one input partition its requirement or criteria name is no longer handled as they say |
| `spec.wrong-ordering-boundary`     | `src/llm_router/_internal/runtime/router.py::RouterRuntime._call_sync_with_timeout` |      2 | an order or a before/after boundary its requirement names is broken                   |
| `interface.unexpected-interaction` | `src/llm_router/_internal/runtime/router.py::RouterRuntime._call_sync_with_timeout` |      2 | an external interaction its requirement rules out happens anyway                      |

Chosen by the default selection (050): every `spec.*` and `interface.*` class this profile
requires, at each function of the contract's `@impl` scope. Rule operators change operators and
statements; they cannot change what the requirement means.

(verification-profile-treq-timed-out-attempt-stops)=

## Profile · TREQ_TIMED_OUT_ATTEMPT_STOPS

**Verification intent.** Prove that an attempt the router leaves at its timeout starts no
further work: no provider request, no retry and no tool call, while the fallback route
answers the request.

**Models:** {ref}`Routing fallback <test-plan-routing-fallback-model>`

### Required coverage

| Test level         | Boundary   | Representation | M&S target |          Target |
| ------------------ | ---------- | -------------- | ---------- | --------------: |
| System Integration | Substitute | Surrogate      | L0         | **1 criterion** |

**Coverage basis.** The left attempt behaves differently in the two public execution modes:
a synchronous attempt keeps running in its thread and must stop itself, an asynchronous one
is cancelled. Both must start nothing after the router leaves them, so the criterion requires
both paths.

**Representation basis.** A scripted provider substitute answers the first route late with a
tool call: the claim is what the left attempt does with a late answer, not provider fidelity.

### Verification criteria

| Criterion                    | Contract                                      | Test level         | Boundary   | Required paths | Required path IDs | Success criterion                                                                                                                      |
| ---------------------------- | --------------------------------------------- | ------------------ | ---------- | -------------: | ----------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `VC_TIMED_OUT_ATTEMPT_STOPS` | {need}`[[id]] <TREQ_TIMED_OUT_ATTEMPT_STOPS>` | System Integration | Substitute |              2 | `sync` · `async`  | After the router leaves a timed-out attempt, its late tool call runs no tool and sends no further provider request, in sync and async. |

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

| REQUIRED                                                                                                                      | OPTIONAL | N/A                                                                                                                                                                                                                                                                                                       |
| ----------------------------------------------------------------------------------------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `impl.comparison` · `impl.control-flow` · `impl.effect` · `interface.unexpected-interaction` · `spec.wrong-ordering-boundary` | —        | `impl.boundary` · `impl.arithmetic` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.error-status` · `interface.payload-schema` · `architecture.forbidden-edge` · `architecture.layer-bypass` · `spec.wrong-outcome` · `spec.missing-partition` |

#### Fault-group rationale

| Group                 | Why                                                                                                                                                         |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Implementation        | The check whether the attempt was left, its stop and the router telling the attempt it was left are the mechanisms; a dropped check lets the attempt go on. |
| Runtime / dependency  | The timeout that makes the router leave the attempt is the parent requirement's; this contract starts after it.                                             |
| Interface / protocol  | A provider request or a tool call after the router left the attempt is the failure this contract rules out.                                                 |
| Architecture          | No internal layering topology is normative for stopping a left attempt.                                                                                     |
| Specification / model | Nothing may start after the router leaves the attempt: a before/after boundary.                                                                             |

### Semantic mutants

| Fault class                        | Target                                                                      | Budget | Risk                                                                |
| ---------------------------------- | --------------------------------------------------------------------------- | -----: | ------------------------------------------------------------------- |
| `spec.wrong-ordering-boundary`     | `src/llm_router/_internal/runtime/executor.py::_stop_if_left`               |      2 | an order or a before/after boundary its requirement names is broken |
| `spec.wrong-ordering-boundary`     | `src/llm_router/_internal/runtime/executor.py::_LeftAttemptAdapter.execute` |      2 | an order or a before/after boundary its requirement names is broken |
| `interface.unexpected-interaction` | `src/llm_router/_internal/runtime/executor.py::_stop_if_left`               |      2 | an external interaction its requirement rules out happens anyway    |
| `interface.unexpected-interaction` | `src/llm_router/_internal/runtime/executor.py::_LeftAttemptAdapter.execute` |      2 | an external interaction its requirement rules out happens anyway    |

Chosen by the default selection (050): every `spec.*` and `interface.*` class this profile
requires, at each function of the contract's `@impl` scope. Rule operators change operators and
statements; they cannot change what the requirement means.

(verification-profile-treq-attempt-keeps-caller-context)=

## Profile · TREQ_ATTEMPT_KEEPS_CALLER_CONTEXT

**Verification intent.** Prove that an attempt run under an attempt timeout sees the context
variables its caller set: the tool it calls reads the caller's value.

**Models:** {ref}`Routing fallback <test-plan-routing-fallback-model>`

### Required coverage

| Test level         | Boundary   | Representation | M&S target |          Target |
| ------------------ | ---------- | -------------- | ---------- | --------------: |
| System Integration | Substitute | Surrogate      | L0         | **1 criterion** |

**Coverage basis.** Only an attempt timeout moves a synchronous attempt to another thread; an
untimed one runs on the caller's thread. The criterion requires the timed attempt in both
public execution modes: a synchronous one runs in a worker thread, an asynchronous one in the
caller's task.

**Representation basis.** A scripted provider substitute asks for a tool call at once and then
answers: the claim is what the tool sees, not provider fidelity.

### Verification criteria

| Criterion                         | Contract                                           | Test level         | Boundary   | Required paths | Required path IDs | Success criterion                                                                                                                                |
| --------------------------------- | -------------------------------------------------- | ------------------ | ---------- | -------------: | ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `VC_ATTEMPT_KEEPS_CALLER_CONTEXT` | {need}`[[id]] <TREQ_ATTEMPT_KEEPS_CALLER_CONTEXT>` | System Integration | Substitute |              2 | `sync` · `async`  | With an attempt timeout set, the tool the attempt calls reads the value the caller set in a context variable before the call, in sync and async. |

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

| REQUIRED                                       | OPTIONAL | N/A                                                                                                                                                                                                                                                                                                                                                                                      |
| ---------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `impl.control-flow` · `spec.missing-partition` | —        | `impl.comparison` · `impl.boundary` · `impl.effect` · `impl.arithmetic` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.error-status` · `interface.payload-schema` · `interface.unexpected-interaction` · `architecture.forbidden-edge` · `architecture.layer-bypass` · `spec.wrong-outcome` · `spec.wrong-ordering-boundary` |

#### Fault-group rationale

| Group                 | Why                                                                                                                                                                                                                  |
| --------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Implementation        | The helper copies the caller's context and returns the call bound to it, so its one fault site is that return; it holds no effect site, and the copy itself is challenged by the semantic missing-partition mutants. |
| Runtime / dependency  | The timeout itself is the parent requirement's; this contract is about what the attempt sees while it runs.                                                                                                          |
| Interface / protocol  | The provider and the tool are called as before; only the context they run in is at stake.                                                                                                                            |
| Architecture          | No internal layering topology is normative for carrying the context.                                                                                                                                                 |
| Specification / model | The promise holds with and without a timeout and in both modes: a timed attempt that loses the context is a missing partition.                                                                                       |

### Semantic mutants

| Fault class              | Target                                                           | Budget | Risk                                                                                  |
| ------------------------ | ---------------------------------------------------------------- | -----: | ------------------------------------------------------------------------------------- |
| `spec.missing-partition` | `src/llm_router/_internal/runtime/router.py::_in_caller_context` |      2 | one input partition its requirement or criteria name is no longer handled as they say |

Chosen by the default selection (050): every `spec.*` and `interface.*` class this profile
requires, at each function of the contract's `@impl` scope. Rule operators change operators and
statements; they cannot change what the requirement means.

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
| `impl.comparison` · `impl.boundary` · `impl.control-flow`                            | —        | `impl.arithmetic` · `impl.effect` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response`                      |
| `interface.unexpected-interaction` · `spec.wrong-outcome` · `spec.missing-partition` | —        | `interface.error-status` · `interface.payload-schema` · `architecture.forbidden-edge` · `architecture.layer-bypass` · `spec.wrong-ordering-boundary` |

#### Fault-group rationale

| Group                 | Why                                                                                                                                                                                                                                                                                                                   |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Implementation        | The contract is a numeric boundary implemented by truncation/comparison/control-flow decisions. A dropped attempt update or truncation removes the limit. The cap's only effect is the slice that cuts the candidate routes; losing it is the slice bound removed (`impl.boundary`), so `impl.effect` does not apply. |
| Runtime / dependency  | Provider failure is useful to expose multiple attempts, but dependency failure modes do not define the cap itself.                                                                                                                                                                                                    |
| Interface / protocol  | Any provider request beyond the configured limit is directly forbidden by the contract.                                                                                                                                                                                                                               |
| Architecture          | No internal layering topology is part of the route-attempt-count claim.                                                                                                                                                                                                                                               |
| Specification / model | Minimum/intermediate limit partitions and the observable capped outcome are normative; route ordering itself belongs elsewhere.                                                                                                                                                                                       |

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

| REQUIRED                                                                                   | OPTIONAL | N/A                                                                                                                                                                                                                                                                                                                                          |
| ------------------------------------------------------------------------------------------ | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `interface.unexpected-interaction` · `spec.wrong-outcome` · `spec.wrong-ordering-boundary` | —        | `impl.comparison` · `impl.boundary` · `impl.arithmetic` · `impl.control-flow` · `impl.effect` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.error-status` · `interface.payload-schema` · `architecture.forbidden-edge` · `architecture.layer-bypass` · `spec.missing-partition` |

#### Fault-group rationale

| Group                 | Why                                                                                                                                                |
| --------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| Implementation        | Route-order implementation mechanics are owned by the derived technical contract rather than this public Requirement.                              |
| Runtime / dependency  | Dependency failure creates the fallback precondition; timeout/unavailability semantics are owned by their own routing contracts.                   |
| Interface / protocol  | Calling a route before the previously successful route is a directly forbidden public interaction.                                                 |
| Architecture          | No internal layering topology is normative for the public sticky-start outcome.                                                                    |
| Specification / model | The visible next-start outcome and before/after ordering define the Requirement; broader route-order partitions belong to the TREQ/Feature levels. |

### Semantic mutants

| Fault class                        | Target                                                                                 | Budget | Risk                                                                    |
| ---------------------------------- | -------------------------------------------------------------------------------------- | -----: | ----------------------------------------------------------------------- |
| `spec.wrong-outcome`               | `src/llm_router/_internal/runtime/router.py::RouterRuntime._next_attempt_order`        |      2 | a result its requirement or criteria name is computed or chosen wrongly |
| `spec.wrong-outcome`               | `src/llm_router/_internal/runtime/router.py::RouterRuntime._remember_fallback_success` |      2 | a result its requirement or criteria name is computed or chosen wrongly |
| `spec.wrong-ordering-boundary`     | `src/llm_router/_internal/runtime/router.py::RouterRuntime._next_attempt_order`        |      2 | an order or a before/after boundary its requirement names is broken     |
| `spec.wrong-ordering-boundary`     | `src/llm_router/_internal/runtime/router.py::RouterRuntime._remember_fallback_success` |      2 | an order or a before/after boundary its requirement names is broken     |
| `interface.unexpected-interaction` | `src/llm_router/_internal/runtime/router.py::RouterRuntime._next_attempt_order`        |      2 | an external interaction its requirement rules out happens anyway        |
| `interface.unexpected-interaction` | `src/llm_router/_internal/runtime/router.py::RouterRuntime._remember_fallback_success` |      2 | an external interaction its requirement rules out happens anyway        |

Chosen by the default selection (050): every `spec.*` and `interface.*` class this profile
requires, at each function of the contract's `@impl` scope. Rule operators change operators and
statements; they cannot change what the requirement means.

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

| REQUIRED                                                                                                            | OPTIONAL | N/A                                                                                                                                                                                                                                                                                                                 |
| ------------------------------------------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `impl.comparison` · `impl.control-flow` · `impl.effect` · `spec.missing-partition` · `spec.wrong-ordering-boundary` | —        | `impl.boundary` · `impl.arithmetic` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.unexpected-interaction` · `interface.error-status` · `interface.payload-schema` · `architecture.forbidden-edge` · `architecture.layer-bypass` · `spec.wrong-outcome` |

#### Fault-group rationale

| Group                 | Why                                                                                                                                       |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| Implementation        | Comparison and branch/order changes can move or lose the selected route identity. A dropped start-position update loses the sticky order. |
| Runtime / dependency  | No external runtime behavior is part of this local ordering invariant.                                                                    |
| Interface / protocol  | Provider interaction order is verified at the parent/Feature level, not by this local technical contract.                                 |
| Architecture          | Route ordering does not require a particular package-layer edge.                                                                          |
| Specification / model | Missing ordering partitions or wrong before/after ordering directly invalidate the technical invariant set.                               |

### Semantic mutants

| Fault class                    | Target                                                       | Budget | Risk                                                                                  |
| ------------------------------ | ------------------------------------------------------------ | -----: | ------------------------------------------------------------------------------------- |
| `spec.missing-partition`       | `src/llm_router/_internal/runtime/routes.py::ordered_routes` |      2 | one input partition its requirement or criteria name is no longer handled as they say |
| `spec.wrong-ordering-boundary` | `src/llm_router/_internal/runtime/routes.py::ordered_routes` |      2 | an order or a before/after boundary its requirement names is broken                   |

Chosen by the default selection (050): every `spec.*` and `interface.*` class this profile
requires, at each function of the contract's `@impl` scope. Rule operators change operators and
statements; they cannot change what the requirement means.

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

| REQUIRED                                                                             | OPTIONAL                         | N/A                                                                                                                                                                                                                                                                                                             |
| ------------------------------------------------------------------------------------ | -------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `interface.unexpected-interaction` · `interface.error-status` · `spec.wrong-outcome` | `runtime.unavailable-disconnect` | `impl.comparison` · `impl.boundary` · `impl.arithmetic` · `impl.control-flow` · `impl.effect` · `runtime.latency-timeout` · `runtime.malformed-response` · `interface.payload-schema` · `architecture.forbidden-edge` · `architecture.layer-bypass` · `spec.missing-partition` · `spec.wrong-ordering-boundary` |

#### Fault-group rationale

| Group                 | Why                                                                                                                                  |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| Implementation        | Internal limiter and selection mechanics are owned by the derived TREQ contracts.                                                    |
| Runtime / dependency  | Provider unavailability is a useful non-blocking challenge to public routing progress; other dependency classes are owned elsewhere. |
| Interface / protocol  | A blocked route must not be contacted and provider error status is a concrete public failure source.                                 |
| Architecture          | No internal layering edge is itself part of the direct public Requirement.                                                           |
| Specification / model | A wrong visible routing outcome invalidates the Requirement; detailed state/ordering partitions belong to TREQ profiles.             |

### Semantic mutants

| Fault class                        | Target                                                                       | Budget | Risk                                                                                      |
| ---------------------------------- | ---------------------------------------------------------------------------- | -----: | ----------------------------------------------------------------------------------------- |
| `spec.wrong-outcome`               | `src/llm_router/_internal/runtime/router.py::RouterRuntime._prepare_request` |      2 | a result its requirement or criteria name is computed or chosen wrongly                   |
| `interface.unexpected-interaction` | `src/llm_router/_internal/runtime/router.py::RouterRuntime._prepare_request` |      2 | an external interaction its requirement rules out happens anyway                          |
| `interface.error-status`           | `src/llm_router/_internal/runtime/router.py::RouterRuntime._prepare_request` |      2 | an error the interface must report comes out with the wrong type or status, or not at all |

Chosen by the default selection (050): every `spec.*` and `interface.*` class this profile
requires, at each function of the contract's `@impl` scope. Rule operators change operators and
statements; they cannot change what the requirement means.

(verification-profile-treq-rate-limit-state)=

## Profile · TREQ_RATE_LIMIT_STATE

**Verification intent.** Prove provider/key isolation, conservative request spacing, failure
recording and success reset as local limiter-state invariants.

**Models:** {ref}`Rate-limit-aware routing <test-plan-rate-limit-routing-model>`

### Required coverage

| Test level | Boundary | Representation | M&S target |         Target |
| ---------- | -------- | -------------- | ---------- | -------------: |
| Component  | Local    | Actual         | —          | **4 criteria** |

**Coverage basis.** The technical contract owns four state invariants with explicit
provider/key and RPS/RPM partitions.

**Representation basis.** Unit tests execute the actual local limiter implementation;
there is no external model or provider boundary.

### Verification criteria

| Criterion                              | Contract                               | Test level | Boundary | Required paths | Required path IDs                                     | Success criterion                                                                                                               |
| -------------------------------------- | -------------------------------------- | ---------- | -------- | -------------: | ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `VC_RATE_LIMIT_PROVIDER_KEY_ISOLATION` | {need}`[[id]] <TREQ_RATE_LIMIT_STATE>` | Component  | Local    |              2 | `same-provider-other-key` · `same-key-other-provider` | State in one provider/key bucket does not block another key of that provider or the same key ID under another provider.         |
| `VC_RATE_LIMIT_CONSERVATIVE_INTERVAL`  | {need}`[[id]] <TREQ_RATE_LIMIT_STATE>` | Component  | Local    |              2 | `rpm-dominant` · `rps-dominant`                       | The limiter uses the longer spacing interval in both RPS-dominant and RPM-dominant configurations.                              |
| `VC_RATE_LIMIT_FAILURE_RECORDED`       | {need}`[[id]] <TREQ_RATE_LIMIT_STATE>` | Component  | Local    |              1 | —                                                     | A failed attempt counts in the transient failure state of its own provider and key: at the threshold that key alone is blocked. |
| `VC_RATE_LIMIT_SUCCESS_RESET`          | {need}`[[id]] <TREQ_RATE_LIMIT_STATE>` | Component  | Local    |              1 | —                                                     | A success clears transient failure count so a later failure sequence must reach the configured threshold again.                 |

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

| REQUIRED                                                                                                                 | OPTIONAL | N/A                                                                                                                                                                                                                                                                                                            |
| ------------------------------------------------------------------------------------------------------------------------ | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `impl.comparison` · `impl.boundary` · `impl.arithmetic` · `impl.control-flow` · `impl.effect` · `spec.missing-partition` | —        | `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.unexpected-interaction` · `interface.error-status` · `interface.payload-schema` · `architecture.forbidden-edge` · `architecture.layer-bypass` · `spec.wrong-outcome` · `spec.wrong-ordering-boundary` |

#### Fault-group rationale

| Group                 | Why                                                                                                                                                                                                                                                                                             |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Implementation        | Comparisons, thresholds, and branch/reset logic directly implement the technical state invariants. A dropped state write or reset leaves stale limiter state. The next allowed time and the remaining wait are sums and differences of timestamps; a swapped operator waits for the wrong time. |
| Runtime / dependency  | The invariants are local state behavior and do not depend on an external provider fault mode.                                                                                                                                                                                                   |
| Interface / protocol  | No external payload or interaction shape is normative for this TREQ.                                                                                                                                                                                                                            |
| Architecture          | No package-layer edge is part of the state invariant.                                                                                                                                                                                                                                           |
| Specification / model | Missing provider/key or interval partitions would leave part of the technical contract unproved.                                                                                                                                                                                                |

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

| REQUIRED                                                                                         | OPTIONAL | N/A                                                                                                                                                                                                                                                                                                                                    |
| ------------------------------------------------------------------------------------------------ | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `impl.comparison` · `impl.boundary` · `impl.control-flow` · `impl.effect` · `spec.wrong-outcome` | —        | `impl.arithmetic` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.unexpected-interaction` · `interface.error-status` · `interface.payload-schema` · `architecture.forbidden-edge` · `architecture.layer-bypass` · `spec.missing-partition` · `spec.wrong-ordering-boundary` |

#### Fault-group rationale

| Group                 | Why                                                                                                                      |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| Implementation        | Threshold comparisons and control flow directly determine the transition. A dropped cooldown write skips the transition. |
| Runtime / dependency  | External provider behavior may cause failures but does not define the configured threshold semantics.                    |
| Interface / protocol  | No provider payload shape is part of this local TREQ.                                                                    |
| Architecture          | No package-layer topology is normative for the cooldown rule.                                                            |
| Specification / model | A wrong blocked/unblocked outcome at the threshold directly violates the policy.                                         |

### Semantic mutants

| Fault class          | Target                                                                     | Budget | Risk                                                                    |
| -------------------- | -------------------------------------------------------------------------- | -----: | ----------------------------------------------------------------------- |
| `spec.wrong-outcome` | `src/llm_router/_internal/runtime/limiter.py::LimiterState.record_failure` |      2 | a result its requirement or criteria name is computed or chosen wrongly |

Chosen by the default selection (050): every `spec.*` and `interface.*` class this profile
requires, at each function of the contract's `@impl` scope. Rule operators change operators and
statements; they cannot change what the requirement means.

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

| REQUIRED                                                                                                                                                    | OPTIONAL | N/A                                                                                                                                                                                                                                                                         |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `impl.comparison` · `impl.control-flow` · `impl.effect` · `interface.unexpected-interaction` · `architecture.layer-bypass` · `spec.wrong-ordering-boundary` | —        | `impl.boundary` · `impl.arithmetic` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.error-status` · `interface.payload-schema` · `architecture.forbidden-edge` · `spec.wrong-outcome` · `spec.missing-partition` |

#### Fault-group rationale

| Group                 | Why                                                                                                                                   |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| Implementation        | Candidate comparisons and control flow choose which available route/key runs. A dropped candidate update runs the wrong route or key. |
| Runtime / dependency  | Provider transport failures are not the selection rule itself.                                                                        |
| Interface / protocol  | Contacting a blocked candidate while an immediately available alternative exists is a forbidden interaction.                          |
| Architecture          | Availability-aware selection must consult limiter state; bypassing that layer recreates avoidable waiting.                            |
| Specification / model | Earliest-availability and available-before-wait ordering are the normative technical semantics.                                       |

### Semantic mutants

| Fault class                        | Target                                                                              | Budget | Risk                                                                |
| ---------------------------------- | ----------------------------------------------------------------------------------- | -----: | ------------------------------------------------------------------- |
| `spec.wrong-ordering-boundary`     | `src/llm_router/_internal/runtime/router.py::RouterRuntime._select_blocked_request` |      2 | an order or a before/after boundary its requirement names is broken |
| `interface.unexpected-interaction` | `src/llm_router/_internal/runtime/router.py::RouterRuntime._select_blocked_request` |      2 | an external interaction its requirement rules out happens anyway    |

Chosen by the default selection (050): every `spec.*` and `interface.*` class this profile
requires, at each function of the contract's `@impl` scope. Rule operators change operators and
statements; they cannot change what the requirement means.
