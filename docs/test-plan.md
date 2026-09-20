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

(test-plan-provider-retry-model)=

### Provider retry

| Layer              | Required denominator                                                                                                   |
| ------------------ | ---------------------------------------------------------------------------------------------------------------------- |
| Component          | explicit status/exception retry classification partitions selected by the verification profile                         |
| System integration | synchronous/asynchronous retryable, permanent, and exhausted same-route workflows selected by the verification profile |

**Design:** status/exception partitioning · sync/async equivalence · attempt-budget boundary analysis · same-route interaction counting

**Completion:** required criteria = **100%** · declared retained paths = **100%**

(test-plan-structured-recovery-model)=

### Structured-output recovery

| Layer              | Required denominator                                                                                      |
| ------------------ | --------------------------------------------------------------------------------------------------------- |
| Component          | bounded repair-prompt property over dynamic schema metadata, invalid output, and validation detail        |
| System integration | successful repair plus minimum/intermediate total-attempt boundaries selected by the verification profile |

**Design:** state-transition testing · boundary-value analysis for total attempt budgets · invalid-payload partitioning · property-based prompt-size control

**Completion:** required criteria = **100%** · declared retained paths = **100%**

(test-plan-data-safety-observability-audit-model)=

### Data-safety observability audit

| Layer              | Required denominator                                                                                                                                |
| ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| System integration | one representative public tool request observed by runtime logging and physically persisted through the actual VCR pre-serialization/write pipeline |

**Design:** end-to-end negative information-flow audit · protected prompt/credential/tool argument/tool-result markers · full structured-log scan · physical cassette scan

**Completion:** required criteria = **100%** · declared retained paths = **100%**

(test-plan-sensitive-runtime-diagnostics-model)=

### Sensitive runtime diagnostics

| Layer              | Required denominator                                                                                              |
| ------------------ | ----------------------------------------------------------------------------------------------------------------- |
| Component          | centralized safe log-context field selection                                                                      |
| System integration | provider-error, local-tool-failure, and schema-validation failure partitions selected by the verification profile |

**Design:** negative information-flow assertions · hostile provider error payload · secret-bearing tool cause/arguments · secret-bearing schema-invalid value · full structured-log-record inspection

**Completion:** required criteria = **100%** · declared retained paths = **100%**

(test-plan-vcr-redaction-model)=

### Durable VCR redaction

| Layer              | Required denominator                                                                                                                                                                                  |
| ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| System integration | authentication/account-data redaction, raw caller request/tool payload redaction, and caller-controlled provider-response echo redaction through the actual VCR pre-serialization and replay pipeline |

**Design:** temp-cassette physical serialization · post-write secret scan · deterministic request-body fingerprint · offline replay after the live server is gone

**Completion:** required criteria = **100%** · declared retained paths = **100%**

(test-plan-provider-adapter-model)=

### Provider adapter boundaries

| Layer                 | Required denominator                                                                                               |
| --------------------- | ------------------------------------------------------------------------------------------------------------------ |
| Component integration | every supported provider family and each distinct transport/failure partition selected by the verification profile |
| System integration    | workflows whose semantics require public-runtime ordering or retry behavior across the adapter boundary            |

**Design:** provider-family partitioning · native transport selection · request/response translation · malformed/error/disconnect partitions · upload-before-chat ordering

**Completion:** required criteria = **100%** · declared retained paths = **100%**

(test-plan-async-provider-model)=

### Asynchronous provider execution

| Layer              | Required denominator                                                                                                                                                         |
| ------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| System integration | every supported provider-family × declared async capability partition: text, structured output, image, document, local video, and remote video where that capability applies |

**Design:** provider-family × capability partitioning · async public entry point · async-only media branches · normalized/grounded response checks

**Completion:** required criteria = **100%** · declared retained paths = **100%**

(test-plan-response-normalization-model)=

### Provider response normalization

| Layer              | Required denominator                                                                                          |
| ------------------ | ------------------------------------------------------------------------------------------------------------- |
| Component          | every supported usage-metadata shape selected by the profile                                                  |
| System integration | each non-baseline provider family independently compared with the OpenAI-compatible canonical public response |

**Design:** provider-shape partitioning · semantic equivalence · stable usage totals · provider-detail non-leakage

**Completion:** required criteria = **100%** · declared retained paths = **100%**

(test-plan-provider-error-boundary-model)=

### Public provider-error boundary

| Layer              | Required denominator                                                                                          |
| ------------------ | ------------------------------------------------------------------------------------------------------------- |
| System integration | at least one HTTP-client failure partition and one SDK-originated failure partition through the public router |

**Design:** transport-family partitioning · hostile provider detail · stable public error type/metadata · provider interaction counting

**Completion:** required criteria = **100%** · declared retained paths = **100%**

(test-plan-session-lifecycle-model)=

### Session lifecycle

| Layer                 | Required denominator                                                             |
| --------------------- | -------------------------------------------------------------------------------- |
| Component integration | history inclusion, one-shot history suppression, fork isolation, and clear/reuse |
| System                | concurrent public requests preserving both session history and routing isolation |

**Design:** state-transition testing · copy-vs-share semantics · explicit history suppression · clear/reuse · concurrent isolation

**Completion:** required criteria = **100%** · declared retained paths = **100%**

(test-plan-session-persistence-model)=

### Session persistence

| Layer                 | Required denominator                                                                                                  |
| --------------------- | --------------------------------------------------------------------------------------------------------------------- |
| Component             | generated text/metadata round-trip; file/image/local-video/remote-video serialization; incompatible-version rejection |
| Component integration | public Session save/load round-trip                                                                                   |

**Design:** property-based round-trip · binary media preservation · serialization-version boundary · public lifecycle round-trip

**Completion:** required criteria = **100%** · declared retained paths = **100%**

(test-plan-public-api-model)=

### Public package surface

| Layer     | Required denominator                                                        |
| --------- | --------------------------------------------------------------------------- |
| Component | the complete current package-declared public surface (`llm_router.__all__`) |

**Design:** authoritative export-set enumeration · package-root resolution

**Completion:** required criteria = **100%** · declared retained paths = **100%**

(test-plan-example-import-safety-model)=

### Executable example import safety

| Layer     | Required denominator                                                                     |
| --------- | ---------------------------------------------------------------------------------------- |
| Component | every shipped Python example module under `examples/llm_router`, excluding `__init__.py` |

**Design:** fresh-module import · network sentinel · live-router call sentinel · one retained path per shipped module

**Completion:** required criteria = **100%** · declared retained paths = **100%**

(test-plan-structured-output-provider-matrix)=

### Structured output provider matrix

| Layer              | Required denominator                               |
| ------------------ | -------------------------------------------------- |
| System integration | every adapter family declaring JSON-schema support |

**Design:** provider-family capability partitioning · one caller schema across routes · public structured-result equivalence · provider-format non-leakage

**Completion:** required criteria = **100%** · declared retained paths = **100%**

(test-plan-grounded-media-matrix)=

### Grounded multimodal provider matrix

| Layer              | Required denominator                                                                                                                                      |
| ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| System integration | every adapter family declaring the relevant media capability together with JSON-schema support; video is partitioned into local-file and remote-URL modes |

**Design:** provider-family capability partitioning · retained known media · schema-valid structured result · deterministic grounding assertions · local-vs-remote video partitioning

**Completion:** required criteria = **100%** · declared retained paths = **100%**

(test-plan-schema-contract-model)=

### Provider-independent schema validation

| Layer     | Required denominator                                                                        |
| --------- | ------------------------------------------------------------------------------------------- |
| Component | Pydantic reconstruction, valid mapping-schema enforcement, invalid mapping-schema rejection |

**Design:** Draft 2020-12 object-schema validation · nested/common constraint enforcement · fail-closed schema normalization · requested-model reconstruction

**Completion:** required criteria = **100%** · declared retained paths = **100%**

(test-plan-content-normalization-model)=

### Multimodal content normalization

| Layer     | Required denominator                                                                                                   |
| --------- | ---------------------------------------------------------------------------------------------------------------------- |
| Component | ordered mixed parts/descriptor metadata, ChatMessage semantics, unsupported input/media, raw-image mode/min/max bounds |
| System    | representative invalid public requests proving zero provider-boundary interactions                                     |

**Design:** ordered-part equivalence · descriptor metadata preservation · mutable-meta copy semantics · boundary-value analysis · pre-provider negative interaction control

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

(test-plan-upper-level-assurance)=

## Upper-level assurance and validation

Requirement/TREQ Verification Profiles prove individual normative contracts. Feature, Goal, and whole-product monitors add only evidence that cannot be reduced to one child contract in isolation.

| Owner level      | Child-support gate      | Direct upper-level evidence                       | Purpose                                                               |
| ---------------- | ----------------------- | ------------------------------------------------- | --------------------------------------------------------------------- |
| Feature          | all direct Requirements | Capability integration · Capability validation    | prove cross-Requirement interaction and the capability's intended use |
| Goal             | all direct Features     | Cross-capability integration · Outcome validation | prove cross-Feature behavior and the Goal-level outcome               |
| Product / System | all current Goals       | Cross-goal integration · Operational validation   | prove whole-product interactions and intended operation               |

**Ownership rule.** Cross evidence belongs to the lowest common assurance owner of the claims it connects: TREQ × TREQ → REQ, REQ × REQ → Feature, Feature × Feature → Goal, Goal × Goal → Product / System. The same upper-level criterion is never copied into its descendants.

**Target source.** This Test Plan defines the allowed assurance kinds and completion rules. A branch-specific Assurance Profile declares the concrete integration/validation criteria before execution. Existing tests never create or weaken a Target merely by existing.

**Methods.** A declared validation criterion may be satisfied by an appropriate retained test, analysis, inspection, demonstration, manual test, or engineering/operational experiment. The method and environment are part of the criterion Target; stronger evidence may replace a weaker method only when the profile explicitly permits it.

**Status semantics.** A declared criterion is `PASS` only when every required retained execution/evaluation passes. A declared but missing or failing criterion is `FAIL`. A section with no declared Target is `N/A`. An applicable child Goal/Feature/Requirement that has not yet been onboarded into the assurance pipeline is `UNKNOWN`, not `N/A` and never implicit `PASS`.

**Completion.** child support = **100% of required direct children PASS** · declared upper-level criteria = **100% PASS**. `N/A` sections do not block; `UNKNOWN` required child support does block whole-product assurance.
