(verification-profile-req-invalid-configuration-errors)=

# Verification profile · Invalid configuration

**Normative contract:** {need}`[[id]] <REQ_INVALID_CONFIGURATION_ERRORS>`

This profile owns verification design for `REQ_INVALID_CONFIGURATION_ERRORS`. The Requirement and its
derived Technical requirements own the product semantics; this page only chooses how those contracts
are demonstrated.

**Verification intent.** Exercise the public rejection boundary for representative invalid configuration,
and directly verify each derived configuration constraint where a lower-level check is clearer and more
diagnostic than repeating the same rule through the public scenario layer.

**Models:** {ref}`Configuration validation <test-plan-configuration-validation-model>` · {ref}`Fault-based testing <test-plan-fault-model>`

## Profile · REQ_INVALID_CONFIGURATION_ERRORS

### Required coverage

| Test level | Boundary | Representation |          Target |
| ---------- | -------- | -------------- | --------------: |
| Component  | Local    | Actual         |  **5 criteria** |
| System     | Local    | Actual         | **1 criterion** |

**Coverage basis.** Component coverage checks the five derived configuration constraints. System coverage
checks the parent Requirement at the public boundary with a representative invalid request.

**Representation basis.** Both required cells execute the actual llm-router implementation. No provider
surrogate is required because the parent Requirement requires rejection before provider execution.

(verification-profile-criteria)=

### Verification criteria

| Criterion                                   | Contract                                          | Test level | Success criterion                                                                                                   |
| ------------------------------------------- | ------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------- |
| `VC_CONFIG_PROVIDER_IDENTITY`               | {need}`[[id]] <TREQ_CONFIG_PROVIDER_IDENTITY>`    | Component  | A mismatched provider key and provider identity is rejected as invalid configuration.                               |
| `VC_CONFIG_MODEL_DECLARATION`               | {need}`[[id]] <TREQ_CONFIG_MODEL_DECLARATION>`    | Component  | An undeclared requested model is rejected before provider execution.                                                |
| `VC_CONFIG_REQUIRED_BASE_URL`               | {need}`[[id]] <TREQ_CONFIG_REQUIRED_BASE_URL>`    | Component  | A provider that requires an explicit base URL is rejected when that URL is absent.                                  |
| `VC_CONFIG_ATTEMPT_TIMEOUT`                 | {need}`[[id]] <TREQ_CONFIG_ATTEMPT_TIMEOUT>`      | Component  | A zero or negative effective attempt timeout is rejected.                                                           |
| `VC_CONFIG_RETRY_ATTEMPTS`                  | {need}`[[id]] <TREQ_CONFIG_RETRY_ATTEMPTS>`       | Component  | An effective retry maximum-attempt count below one is rejected.                                                     |
| `VC_INVALID_CONFIGURATION_PUBLIC_REJECTION` | {need}`[[id]] <REQ_INVALID_CONFIGURATION_ERRORS>` | System     | A public request with invalid configuration surfaces a public configuration error and performs no provider request. |

The criterion ID is a stable verification-design identifier. Test level, boundary, representation, and
the executable test that supplies evidence are **not encoded in the ID** and may change independently.

### Evidence aggregation

| Signal                 | Rule | Applies to                                                        |
| ---------------------- | ---- | ----------------------------------------------------------------- |
| Semantic coverage      | ALL  | required verification criteria                                    |
| Representation         | ALL  | retained evidence for satisfied criteria                          |
| Provenance             | ALL  | retained evidence for satisfied criteria                          |
| Producer qualification | ALL  | retained evidence for satisfied criteria; every required producer |
| Freshness              | ALL  | retained evidence for satisfied criteria                          |
| M&S validation         | ALL  | applicable surrogate/model evidence                               |

### Fault applicability

| REQUIRED                                                                         | OPTIONAL                      | N/A                                                             |
| -------------------------------------------------------------------------------- | ----------------------------- | --------------------------------------------------------------- |
| `impl.comparison` · `impl.boundary` · `impl.control-flow`                        | `runtime.latency-timeout`     | `runtime.unavailable-disconnect` · `runtime.malformed-response` |
| `interface.unexpected-interaction`                                               | `architecture.forbidden-edge` | `interface.error-status` · `interface.payload-schema`           |
| `spec.wrong-outcome` · `spec.missing-partition` · `spec.wrong-ordering-boundary` | —                             | `architecture.layer-bypass`                                     |

#### Fault-group rationale

| Group                 | Why                                                                                            |
| --------------------- | ---------------------------------------------------------------------------------------------- |
| Implementation        | Configuration validation logic itself can be wrong.                                            |
| Runtime / dependency  | Not required because the parent Requirement must fail before dependency runtime is reached.    |
| Interface / protocol  | Unexpected provider interaction violates the required pre-provider failure boundary.           |
| Architecture          | Not required because these contracts do not assert a particular internal layering design.      |
| Specification / model | The contracts define the public outcome, configuration constraints, and pre-provider ordering. |

### Blocking mutation checks

| Test level | Required checks                       |
| ---------- | ------------------------------------- |
| Component  | Mutation Reach · Mutation Sensitivity |
| System     | Mutation Reach · Mutation Sensitivity |

Uses the {ref}`project mutation floor <test-plan>`.
