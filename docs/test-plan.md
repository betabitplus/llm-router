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

**Completion:** required coverage = **100%**

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

**Completion:** required fault-class coverage = **100%** · required deterministic fault detection = **100%**
