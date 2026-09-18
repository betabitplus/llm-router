(test-plan)=

# Test plan

## Project decisions

| Decision                      |                    Value | Effect                                                                       |
| ----------------------------- | -----------------------: | ---------------------------------------------------------------------------- |
| Mutation Reach floor          |                **≥ 80%** | blocking when a Requirement selects mutation                                 |
| Mutation Sensitivity floor    |                **≥ 80%** | blocking when a Requirement selects mutation                                 |
| Evidence freshness            | **current retained run** | retained verification evidence must belong to the current retained execution |
| Retained mutmut Test Strength |           **diagnostic** | non-blocking unless a Requirement explicitly overrides it                    |

(test-plan-test-models)=

## Reusable Test Models

(test-plan-configuration-validation-model)=

### Configuration validation

| Layer     | Required denominator                                                                  |
| --------- | ------------------------------------------------------------------------------------- |
| Component | every applicable configuration-validity contract selected by the verification profile |
| System    | verification-profile-selected representative public path(s)                           |

**Design:** equivalence partitioning · boundary value analysis

**Completion:** required criteria = **100%** · declared retained paths = **100%**

(test-plan-configuration-precedence-model)=

### Configuration precedence

| Layer              | Required denominator                                                                                   |
| ------------------ | ------------------------------------------------------------------------------------------------------ |
| Component          | generated omission-vs-explicit-value semantics selected by the verification profile                    |
| System integration | selected public override/clearing scenarios observed across the configured provider-interface boundary |

**Design:** precedence partitioning · omission vs explicit value · explicit clear/null semantics

**Completion:** required coverage = **100%**

(test-plan-credential-resolution-model)=

### Credential resolution

| Layer     | Required denominator                                                                                                                                                               |
| --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Component | selected key-source partitions: configured fixed key, automatic rotation, required missing, plus every provider family explicitly permitted to run with an optional missing bearer |
| System    | selected public missing-credential error path                                                                                                                                      |

**Design:** equivalence partitioning · key-source precedence · provider-family optional-credential partitioning · deterministic rotation

**Completion:** required criteria = **100%** · declared retained paths = **100%**

(test-plan-config-activation-model)=

### Configuration activation

| Layer              | Required denominator                                                                                                         |
| ------------------ | ---------------------------------------------------------------------------------------------------------------------------- |
| Component          | replacement snapshot round-trip, subsequent runtime snapshot capture, and selected cache invalidation                        |
| System integration | a public request created after installation exhibits a replacement-derived runtime effect at an observable provider boundary |

**Design:** state transition · replacement snapshot · stale-cache negative control · post-install behavioral observation

**Completion:** required criteria = **100%** · declared retained paths = **100%**

(test-plan-tool-selection-model)=

### Tool selection

| Layer              | Required denominator                                                                                                                         |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------- |
| Component          | every supported public named-choice input form plus each distinct provider named-choice serialization implementation selected by the profile |
| System integration | every provider-family partition selected by the verification profile, with each declared retained path present and passing                   |

**Design:** public input-form partitioning · provider-family capability partitioning · explicit named choice vs alternate registered tool · provider-boundary request inspection

**Completion:** required criteria = **100%** · declared retained paths = **100%**

(test-plan-tool-execution-model)=

### Tool execution

| Layer              | Required denominator                                                                                                           |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------ |
| Component          | verification-profile-selected registry semantics: duplicate rejection, callable schema/execution, supported call-shape parsing |
| System integration | selected multi-round and runtime-safety workflows, including every provider-family partition declared by the profile           |

**Design:** state-transition testing · provider-family capability partitioning · tool-result round trip · public error boundary · bounded round termination

**Completion:** required criteria = **100%** · declared retained paths = **100%**

(test-plan-routing-fallback-model)=

### Routing fallback

| Layer              | Required denominator                                                                                                                          |
| ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------- |
| Component          | route-order and route-attempt boundary criteria selected by the verification profile                                                          |
| System integration | public fallback, timeout, attempt-cap, and sticky-start workflows selected by the verification profile through a controlled provider boundary |

**Design:** failure partitioning · timeout with/without fallback · boundary-value analysis for route caps · route-order identity · sticky-start state transition

**Completion:** required criteria = **100%** · declared retained paths = **100%**

(test-plan-rate-limit-routing-model)=

### Rate-limit-aware routing

| Layer              | Required denominator                                                                                                                             |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| Component          | provider/key isolation, both conservative-interval dominance directions, success reset, and cooldown-threshold state selected by the profile     |
| System integration | blocked-route skip, all-blocked fail/wait, earliest-availability selection, and auto-key availability/rotation workflows selected by the profile |

**Design:** state-transition testing · provider/key partitioning · timing-boundary analysis · availability ordering · negative interaction control

**Completion:** required criteria = **100%** · declared retained paths = **100%**

(test-plan-fault-model)=

### Fault-based testing

| Group                 | Fault classes                                                                               |
| --------------------- | ------------------------------------------------------------------------------------------- |
| Implementation        | `impl.comparison` · `impl.boundary` · `impl.control-flow`                                   |
| Runtime / dependency  | `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` |
| Interface / protocol  | `interface.unexpected-interaction` · `interface.error-status` · `interface.payload-schema`  |
| Architecture          | `architecture.forbidden-edge` · `architecture.layer-bypass`                                 |
| Specification / model | `spec.wrong-outcome` · `spec.missing-partition` · `spec.wrong-ordering-boundary`            |

#### Fault-class semantics

| Fault class                        | Meaning                                                                            |
| ---------------------------------- | ---------------------------------------------------------------------------------- |
| `impl.comparison`                  | A comparison/operator change alters the implementation decision.                   |
| `impl.boundary`                    | A boundary value or threshold change alters accepted vs rejected behavior.         |
| `impl.control-flow`                | A branch, return, or exception-flow change alters execution.                       |
| `runtime.latency-timeout`          | Dependency latency or timeout behavior challenges the runtime path.                |
| `runtime.unavailable-disconnect`   | Dependency unavailability or disconnect challenges the runtime path.               |
| `runtime.malformed-response`       | Dependency returns malformed or unparsable data.                                   |
| `interface.unexpected-interaction` | The system performs an external interaction that the contract says must not occur. |
| `interface.error-status`           | The external interface returns an error status.                                    |
| `interface.payload-schema`         | The external payload violates the expected schema or shape.                        |
| `architecture.forbidden-edge`      | A forbidden dependency edge crosses an architectural boundary.                     |
| `architecture.layer-bypass`        | Execution bypasses a required architectural layer or boundary.                     |
| `spec.wrong-outcome`               | The observable outcome differs from the Requirement.                               |
| `spec.missing-partition`           | A Requirement-relevant semantic partition is absent from verification.             |
| `spec.wrong-ordering-boundary`     | Observable ordering or before/after boundary semantics are wrong.                  |

For retained pytest evidence, a fault class is challenged only when the test declares
the exact `contract_id + fault class` and the same execution retains a matching
runtime fault-injection observation. A marker without the runtime observation is not
fault evidence.

**Completion:** required fault-class coverage = **100%** · required deterministic fault detection = **100%**
