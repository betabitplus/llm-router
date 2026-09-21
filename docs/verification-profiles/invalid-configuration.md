(verification-profile-req-invalid-configuration-errors)=

# Verification profiles · Invalid configuration

These profiles own verification design for {need}`REQ_INVALID_CONFIGURATION_ERRORS`
and its derived configuration-validity Technical requirements. Product semantics stay
in the normative Requirement/TREQ cards; this page selects evidence boundaries,
denominators, and fault applicability without collapsing child Technical requirements
into the parent public contract.

## Profile · REQ_INVALID_CONFIGURATION_ERRORS

**Verification intent.** Prove at the public router boundary that an applicable invalid
effective configuration is rejected as ConfigurationError before provider execution.
The concrete validity rules are owned and verified by the thirteen derived Technical
requirements below.

**Models:** {ref}`Configuration validation <test-plan-configuration-validation-model>` ·
{ref}`Fault-based testing <test-plan-fault-model>`

### Required coverage

| Test level | Boundary | Representation | M&S target |          Target |
| ---------- | -------- | -------------- | ---------- | --------------: |
| System     | Local    | Actual         | —          | **1 criterion** |

**Coverage basis.** The parent Requirement owns one public rejection outcome. It does
not duplicate the thirteen technical validation-rule denominators.

**Representation basis.** The retained public path executes the actual router and
configuration validation implementation. No provider surrogate is required because the
contract requires failure before provider execution.

(verification-profile-criteria)=

### Verification criteria

| Criterion                                   | Contract                                          | Test level | Boundary | Required paths | Success criterion                                                                                         |
| ------------------------------------------- | ------------------------------------------------- | ---------- | -------- | -------------: | --------------------------------------------------------------------------------------------------------- |
| `VC_INVALID_CONFIGURATION_PUBLIC_REJECTION` | {need}`[[id]] <REQ_INVALID_CONFIGURATION_ERRORS>` | System     | Local    |              1 | A public request with invalid configuration surfaces ConfigurationError and performs no provider request. |

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

| Technical requirement                                                                              | Target |
| -------------------------------------------------------------------------------------------------- | ------ |
| {need}`Configured provider identity is internally consistent <TREQ_CONFIG_PROVIDER_IDENTITY>`      | PASS   |
| {need}`Requested model is declared by the effective configuration <TREQ_CONFIG_MODEL_DECLARATION>` | PASS   |
| {need}`Required provider base URL is present <TREQ_CONFIG_REQUIRED_BASE_URL>`                      | PASS   |
| {need}`Attempt timeout is positive <TREQ_CONFIG_ATTEMPT_TIMEOUT>`                                  | PASS   |
| {need}`Retry attempt limit is positive <TREQ_CONFIG_RETRY_ATTEMPTS>`                               | PASS   |
| {need}`Retry wait bounds are coherent <TREQ_CONFIG_RETRY_WAIT_BOUNDS>`                             | PASS   |
| {need}`Route-attempt limit is positive when configured <TREQ_CONFIG_ROUTE_ATTEMPT_LIMIT>`          | PASS   |
| {need}`Fallback shuffle minimum is positive <TREQ_CONFIG_FALLBACK_SHUFFLE_MIN_ROUTES>`             | PASS   |
| {need}`Default tool-round limit is positive <TREQ_CONFIG_TOOL_ROUND_LIMIT>`                        | PASS   |
| {need}`Structured-output repair limit is positive <TREQ_CONFIG_STRUCTURED_OUTPUT_ATTEMPTS>`        | PASS   |
| {need}`Default provider is declared <TREQ_CONFIG_DEFAULT_PROVIDER_DECLARATION>`                    | PASS   |
| {need}`Default model is executable by the default provider <TREQ_CONFIG_DEFAULT_MODEL_MAPPING>`    | PASS   |
| {need}`Model provider mappings are internally resolvable <TREQ_CONFIG_MODEL_PROVIDER_REFERENCES>`  | PASS   |

### Fault applicability

| REQUIRED                                                                         | OPTIONAL                      | N/A                                                             |
| -------------------------------------------------------------------------------- | ----------------------------- | --------------------------------------------------------------- |
| `impl.comparison` · `impl.boundary` · `impl.control-flow`                        | `runtime.latency-timeout`     | `runtime.unavailable-disconnect` · `runtime.malformed-response` |
| `interface.unexpected-interaction` · `architecture.layer-bypass`                 | `architecture.forbidden-edge` | `interface.error-status` · `interface.payload-schema`           |
| `spec.wrong-outcome` · `spec.missing-partition` · `spec.wrong-ordering-boundary` | —                             | —                                                               |

#### Fault-group rationale

| Group                 | Why                                                                                                                                          |
| --------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| Implementation        | The public pre-provider rejection boundary depends on validation control flow and rejection predicates remaining effective.                  |
| Runtime / dependency  | Provider latency is a useful negative-control challenge; provider disconnect/malformed response cannot determine a pre-provider rejection.   |
| Interface / protocol  | Any provider interaction is itself a violation because applicable invalid configuration must fail before the provider boundary.              |
| Architecture          | A validation-layer bypass can violate pre-provider rejection even when the public API still returns normally.                                |
| Specification / model | Wrong public outcome, omitted invalid partitions, or incorrect ordering of rejection relative to provider execution violate the Requirement. |

### Blocking mutation checks

| Test level | Required checks                       |
| ---------- | ------------------------------------- |
| Component  | Mutation Reach · Mutation Sensitivity |
| System     | Mutation Reach · Mutation Sensitivity |

Uses the {ref}`project mutation floor <test-plan>`.

(verification-profile-treq-config-provider-identity)=

## Profile · TREQ_CONFIG_PROVIDER_IDENTITY

**Verification intent.** Prove that a provider entry whose registered key and declared
provider identity disagree is rejected by the actual local validator.

**Models:** {ref}`Configuration validation <test-plan-configuration-validation-model>`

### Required coverage

| Test level | Boundary | Representation | M&S target |          Target |
| ---------- | -------- | -------------- | ---------- | --------------: |
| Component  | Local    | Actual         | —          | **1 criterion** |

**Coverage basis.** One mismatch partition is required: registered provider key differs from the provider identity stored in that entry.

**Representation basis.** The retained path executes the actual local configuration validation implementation; no material external surrogate or model participant is involved.

### Verification criteria

| Criterion                     | Contract                                       | Test level | Boundary | Required paths | Success criterion                                                                     |
| ----------------------------- | ---------------------------------------------- | ---------- | -------- | -------------: | ------------------------------------------------------------------------------------- |
| `VC_CONFIG_PROVIDER_IDENTITY` | {need}`[[id]] <TREQ_CONFIG_PROVIDER_IDENTITY>` | Component  | Local    |              1 | A mismatched provider key and provider identity is rejected as invalid configuration. |

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

| REQUIRED                                        | OPTIONAL | N/A                                                                                                                                                                                                        |
| ----------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `impl.comparison` · `impl.control-flow`         | —        | `impl.boundary` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.unexpected-interaction` · `interface.error-status` · `interface.payload-schema` |
| `spec.wrong-outcome` · `spec.missing-partition` | —        | `architecture.forbidden-edge` · `architecture.layer-bypass` · `spec.wrong-ordering-boundary`                                                                                                               |

#### Fault-group rationale

| Group                 | Why                                                                                       |
| --------------------- | ----------------------------------------------------------------------------------------- |
| Implementation        | Equality/identity comparison and its rejection branch implement the technical constraint. |
| Runtime / dependency  | The constraint is resolved entirely from local configuration.                             |
| Interface / protocol  | No external protocol interaction is needed to decide provider identity consistency.       |
| Architecture          | The contract does not prescribe internal module topology.                                 |
| Specification / model | Wrong acceptance/rejection or omission of the mismatch partition violates the constraint. |

No blocking mutation threshold is selected.

(verification-profile-treq-config-model-declaration)=

## Profile · TREQ_CONFIG_MODEL_DECLARATION

**Verification intent.** Prove that a requested model absent from the effective model
registry is rejected locally before provider execution.

**Models:** {ref}`Configuration validation <test-plan-configuration-validation-model>`

### Required coverage

| Test level | Boundary | Representation | M&S target |          Target |
| ---------- | -------- | -------------- | ---------- | --------------: |
| Component  | Local    | Actual         | —          | **1 criterion** |

**Coverage basis.** One undeclared-model partition is required because the TREQ has one membership obligation.

**Representation basis.** The retained path executes the actual local configuration validation implementation; no material external surrogate or model participant is involved.

### Verification criteria

| Criterion                     | Contract                                       | Test level | Boundary | Required paths | Success criterion                                                    |
| ----------------------------- | ---------------------------------------------- | ---------- | -------- | -------------: | -------------------------------------------------------------------- |
| `VC_CONFIG_MODEL_DECLARATION` | {need}`[[id]] <TREQ_CONFIG_MODEL_DECLARATION>` | Component  | Local    |              1 | An undeclared requested model is rejected before provider execution. |

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

| REQUIRED                                        | OPTIONAL | N/A                                                                                                                                                                                                        |
| ----------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `impl.comparison` · `impl.control-flow`         | —        | `impl.boundary` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.unexpected-interaction` · `interface.error-status` · `interface.payload-schema` |
| `spec.wrong-outcome` · `spec.missing-partition` | —        | `architecture.forbidden-edge` · `architecture.layer-bypass` · `spec.wrong-ordering-boundary`                                                                                                               |

#### Fault-group rationale

| Group                 | Why                                                                               |
| --------------------- | --------------------------------------------------------------------------------- |
| Implementation        | Registry membership comparison and rejection control flow implement the rule.     |
| Runtime / dependency  | The decision is local and independent of provider availability.                   |
| Interface / protocol  | No provider payload or status participates in model declaration.                  |
| Architecture          | Internal topology is not normative.                                               |
| Specification / model | Accepting an undeclared model or omitting that partition violates the constraint. |

No blocking mutation threshold is selected.

(verification-profile-treq-config-required-base-url)=

## Profile · TREQ_CONFIG_REQUIRED_BASE_URL

**Verification intent.** Prove that a provider requiring an explicit base URL cannot be
accepted when the effective configuration omits that URL.

**Models:** {ref}`Configuration validation <test-plan-configuration-validation-model>`

### Required coverage

| Test level | Boundary | Representation | M&S target |          Target |
| ---------- | -------- | -------------- | ---------- | --------------: |
| Component  | Local    | Actual         | —          | **1 criterion** |

**Coverage basis.** One missing-required-endpoint partition is required for a provider whose configuration declares an explicit base URL mandatory.

**Representation basis.** The retained path executes the actual local configuration validation implementation; no material external surrogate or model participant is involved.

### Verification criteria

| Criterion                     | Contract                                       | Test level | Boundary | Required paths | Success criterion                                                              |
| ----------------------------- | ---------------------------------------------- | ---------- | -------- | -------------: | ------------------------------------------------------------------------------ |
| `VC_CONFIG_REQUIRED_BASE_URL` | {need}`[[id]] <TREQ_CONFIG_REQUIRED_BASE_URL>` | Component  | Local    |              1 | A provider requiring an explicit base URL is rejected when that URL is absent. |

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

| REQUIRED                                        | OPTIONAL | N/A                                                                                                                                                                                                                            |
| ----------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `impl.control-flow`                             | —        | `impl.comparison` · `impl.boundary` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.unexpected-interaction` · `interface.error-status` · `interface.payload-schema` |
| `spec.wrong-outcome` · `spec.missing-partition` | —        | `architecture.forbidden-edge` · `architecture.layer-bypass` · `spec.wrong-ordering-boundary`                                                                                                                                   |

#### Fault-group rationale

| Group                 | Why                                                                                |
| --------------------- | ---------------------------------------------------------------------------------- |
| Implementation        | The requires-base-URL branch must not skip its missing-value rejection.            |
| Runtime / dependency  | Endpoint reachability is outside the local presence constraint.                    |
| Interface / protocol  | Provider protocol behavior is irrelevant before endpoint configuration is valid.   |
| Architecture          | No internal layer edge is normative.                                               |
| Specification / model | Wrong acceptance or omission of the required-base-URL partition violates the rule. |

No blocking mutation threshold is selected.

(verification-profile-treq-config-attempt-timeout)=

## Profile · TREQ_CONFIG_ATTEMPT_TIMEOUT

**Verification intent.** Prove the strict positive lower boundary for effective attempt
timeout.

**Models:** {ref}`Configuration validation <test-plan-configuration-validation-model>`

### Required coverage

| Test level | Boundary | Representation | M&S target |          Target |
| ---------- | -------- | -------------- | ---------- | --------------: |
| Component  | Local    | Actual         | —          | **1 criterion** |

**Coverage basis.** One non-positive lower-bound partition is required; the zero boundary is the retained representative of the invalid class.

**Representation basis.** The retained path executes the actual local configuration validation implementation; no material external surrogate or model participant is involved.

### Verification criteria

| Criterion                   | Contract                                     | Test level | Boundary | Required paths | Success criterion                                         |
| --------------------------- | -------------------------------------------- | ---------- | -------- | -------------: | --------------------------------------------------------- |
| `VC_CONFIG_ATTEMPT_TIMEOUT` | {need}`[[id]] <TREQ_CONFIG_ATTEMPT_TIMEOUT>` | Component  | Local    |              1 | A zero or negative effective attempt timeout is rejected. |

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

| REQUIRED                                        | OPTIONAL | N/A                                                                                                                                                                                                            |
| ----------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `impl.comparison` · `impl.boundary`             | —        | `impl.control-flow` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.unexpected-interaction` · `interface.error-status` · `interface.payload-schema` |
| `spec.wrong-outcome` · `spec.missing-partition` | —        | `architecture.forbidden-edge` · `architecture.layer-bypass` · `spec.wrong-ordering-boundary`                                                                                                                   |

#### Fault-group rationale

| Group                 | Why                                                                                    |
| --------------------- | -------------------------------------------------------------------------------------- |
| Implementation        | The positivity comparison and exact zero boundary implement the constraint.            |
| Runtime / dependency  | This is a local configured-value invariant, not an observed latency contract.          |
| Interface / protocol  | No external protocol participates in timeout-value validity.                           |
| Architecture          | Internal topology is not part of the constraint.                                       |
| Specification / model | Accepting a non-positive timeout or omitting that invalid partition violates the rule. |

No blocking mutation threshold is selected.

(verification-profile-treq-config-retry-attempts)=

## Profile · TREQ_CONFIG_RETRY_ATTEMPTS

**Verification intent.** Prove the minimum valid retry-attempt count is one.

**Models:** {ref}`Configuration validation <test-plan-configuration-validation-model>`

### Required coverage

| Test level | Boundary | Representation | M&S target |          Target |
| ---------- | -------- | -------------- | ---------- | --------------: |
| Component  | Local    | Actual         | —          | **1 criterion** |

**Coverage basis.** One below-one retry-attempt partition is required; zero is the exact lower-bound counterexample.

**Representation basis.** The retained path executes the actual local configuration validation implementation; no material external surrogate or model participant is involved.

### Verification criteria

| Criterion                  | Contract                                    | Test level | Boundary | Required paths | Success criterion                                             |
| -------------------------- | ------------------------------------------- | ---------- | -------- | -------------: | ------------------------------------------------------------- |
| `VC_CONFIG_RETRY_ATTEMPTS` | {need}`[[id]] <TREQ_CONFIG_RETRY_ATTEMPTS>` | Component  | Local    |              1 | A provider-retry maximum-attempt count below one is rejected. |

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

| REQUIRED                                        | OPTIONAL | N/A                                                                                                                                                                                                            |
| ----------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `impl.comparison` · `impl.boundary`             | —        | `impl.control-flow` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.unexpected-interaction` · `interface.error-status` · `interface.payload-schema` |
| `spec.wrong-outcome` · `spec.missing-partition` | —        | `architecture.forbidden-edge` · `architecture.layer-bypass` · `spec.wrong-ordering-boundary`                                                                                                                   |

#### Fault-group rationale

| Group                 | Why                                                                                 |
| --------------------- | ----------------------------------------------------------------------------------- |
| Implementation        | The lower-bound comparison implements the retry-attempt validity rule.              |
| Runtime / dependency  | Retry execution behavior is outside this configuration invariant.                   |
| Interface / protocol  | No provider protocol result is required to validate the configured count.           |
| Architecture          | Internal topology is not normative.                                                 |
| Specification / model | Accepting zero attempts or omitting that invalid partition violates the constraint. |

No blocking mutation threshold is selected.

(verification-profile-treq-config-retry-wait-bounds)=

## Profile · TREQ_CONFIG_RETRY_WAIT_BOUNDS

**Verification intent.** Prove both independent invalid retry-wait partitions: a
non-positive minimum and a maximum below the minimum.

**Models:** {ref}`Configuration validation <test-plan-configuration-validation-model>`

### Required coverage

| Test level | Boundary | Representation | M&S target |          Target |
| ---------- | -------- | -------------- | ---------- | --------------: |
| Component  | Local    | Actual         | —          | **1 criterion** |

**Coverage basis.** Two independent partitions are required: non-positive minimum wait and maximum wait below the minimum.

**Representation basis.** The retained path executes the actual local configuration validation implementation; no material external surrogate or model participant is involved.

### Verification criteria

| Criterion                     | Contract                                       | Test level | Boundary | Required paths | Required path IDs                              | Success criterion                                                                   |
| ----------------------------- | ---------------------------------------------- | ---------- | -------- | -------------: | ---------------------------------------------- | ----------------------------------------------------------------------------------- |
| `VC_CONFIG_RETRY_WAIT_BOUNDS` | {need}`[[id]] <TREQ_CONFIG_RETRY_WAIT_BOUNDS>` | Component  | Local    |              2 | `min-wait-non-positive` · `max-wait-below-min` | Both non-positive minimum and inverted maximum/minimum configurations are rejected. |

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

| REQUIRED                                                                         | OPTIONAL | N/A                                                                                                                                                                                                            |
| -------------------------------------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `impl.comparison` · `impl.boundary`                                              | —        | `impl.control-flow` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.unexpected-interaction` · `interface.error-status` · `interface.payload-schema` |
| `spec.wrong-outcome` · `spec.missing-partition` · `spec.wrong-ordering-boundary` | —        | `architecture.forbidden-edge` · `architecture.layer-bypass`                                                                                                                                                    |

#### Fault-group rationale

| Group                 | Why                                                                                          |
| --------------------- | -------------------------------------------------------------------------------------------- |
| Implementation        | Boundary and relative-order comparisons implement the two independent invalid partitions.    |
| Runtime / dependency  | Runtime retry timing is outside validity of the configured interval.                         |
| Interface / protocol  | No provider interaction is required to validate the wait bounds.                             |
| Architecture          | Internal topology is not normative.                                                          |
| Specification / model | Missing either invalid partition, wrong outcome, or inverted ordering semantics violates it. |

No blocking mutation threshold is selected.

(verification-profile-treq-config-route-attempt-limit)=

## Profile · TREQ_CONFIG_ROUTE_ATTEMPT_LIMIT

**Verification intent.** Prove that an explicitly configured route-attempt maximum
cannot be below one.

**Models:** {ref}`Configuration validation <test-plan-configuration-validation-model>`

### Required coverage

| Test level | Boundary | Representation | M&S target |          Target |
| ---------- | -------- | -------------- | ---------- | --------------: |
| Component  | Local    | Actual         | —          | **1 criterion** |

**Coverage basis.** One configured below-one route-attempt partition is required; zero is the exact lower-bound counterexample.

**Representation basis.** The retained path executes the actual local configuration validation implementation; no material external surrogate or model participant is involved.

### Verification criteria

| Criterion                       | Contract                                         | Test level | Boundary | Required paths | Success criterion                                         |
| ------------------------------- | ------------------------------------------------ | ---------- | -------- | -------------: | --------------------------------------------------------- |
| `VC_CONFIG_ROUTE_ATTEMPT_LIMIT` | {need}`[[id]] <TREQ_CONFIG_ROUTE_ATTEMPT_LIMIT>` | Component  | Local    |              1 | A configured route-attempt maximum below one is rejected. |

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

| REQUIRED                                        | OPTIONAL | N/A                                                                                                                                                                                                            |
| ----------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `impl.comparison` · `impl.boundary`             | —        | `impl.control-flow` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.unexpected-interaction` · `interface.error-status` · `interface.payload-schema` |
| `spec.wrong-outcome` · `spec.missing-partition` | —        | `architecture.forbidden-edge` · `architecture.layer-bypass` · `spec.wrong-ordering-boundary`                                                                                                                   |

#### Fault-group rationale

| Group                 | Why                                                                                 |
| --------------------- | ----------------------------------------------------------------------------------- |
| Implementation        | The lower-bound comparison implements the configured route-attempt invariant.       |
| Runtime / dependency  | Fallback execution behavior is outside this local configuration validity check.     |
| Interface / protocol  | No provider protocol is needed to validate the attempt count.                       |
| Architecture          | Internal topology is not normative.                                                 |
| Specification / model | Accepting zero attempts or omitting that invalid partition violates the constraint. |

No blocking mutation threshold is selected.

(verification-profile-treq-config-fallback-shuffle-min-routes)=

## Profile · TREQ_CONFIG_FALLBACK_SHUFFLE_MIN_ROUTES

**Verification intent.** Prove the minimum configured fallback-shuffle candidate count
is one.

**Models:** {ref}`Configuration validation <test-plan-configuration-validation-model>`

### Required coverage

| Test level | Boundary | Representation | M&S target |          Target |
| ---------- | -------- | -------------- | ---------- | --------------: |
| Component  | Local    | Actual         | —          | **1 criterion** |

**Coverage basis.** One below-one fallback-shuffle threshold partition is required; zero is the exact lower-bound counterexample.

**Representation basis.** The retained path executes the actual local configuration validation implementation; no material external surrogate or model participant is involved.

### Verification criteria

| Criterion                               | Contract                                                 | Test level | Boundary | Required paths | Success criterion                                             |
| --------------------------------------- | -------------------------------------------------------- | ---------- | -------- | -------------: | ------------------------------------------------------------- |
| `VC_CONFIG_FALLBACK_SHUFFLE_MIN_ROUTES` | {need}`[[id]] <TREQ_CONFIG_FALLBACK_SHUFFLE_MIN_ROUTES>` | Component  | Local    |              1 | A fallback-shuffle minimum route count below one is rejected. |

### Evidence aggregation

| Signal                 | Rule | Applies to                                                         |
| ---------------------- | ---- | ------------------------------------------------------------------ |
| Semantic coverage      | ALL  | required verification criteria and each criterion's declared paths |
| Representation         | ALL  | retained evidence for satisfied criteria                           |
| Provenance             | ALL  | retained evidence for satisfied criteria; every required producer  |
| Freshness              | ALL  | retained evidence for satisfied criteria                           |
| Producer qualification | ALL  | retained evidence for satisfied criteria                           |
| M&S validation         | ALL  | applicable surrogate/model evidence                                |

### Fault applicability

| REQUIRED                                        | OPTIONAL | N/A                                                                                                                                                                                                            |
| ----------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `impl.comparison` · `impl.boundary`             | —        | `impl.control-flow` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.unexpected-interaction` · `interface.error-status` · `interface.payload-schema` |
| `spec.wrong-outcome` · `spec.missing-partition` | —        | `architecture.forbidden-edge` · `architecture.layer-bypass` · `spec.wrong-ordering-boundary`                                                                                                                   |

#### Fault-group rationale

| Group                 | Why                                                                               |
| --------------------- | --------------------------------------------------------------------------------- |
| Implementation        | The lower-bound comparison implements the shuffle-threshold validity rule.        |
| Runtime / dependency  | Candidate execution behavior is outside this local configuration invariant.       |
| Interface / protocol  | No provider interaction is required to validate the threshold.                    |
| Architecture          | Internal topology is not normative.                                               |
| Specification / model | Accepting zero routes or omitting that invalid partition violates the constraint. |

No blocking mutation threshold is selected.

(verification-profile-treq-config-tool-round-limit)=

## Profile · TREQ_CONFIG_TOOL_ROUND_LIMIT

**Verification intent.** Prove the configured default maximum tool-round count is at
least one.

**Models:** {ref}`Configuration validation <test-plan-configuration-validation-model>`

### Required coverage

| Test level | Boundary | Representation | M&S target |          Target |
| ---------- | -------- | -------------- | ---------- | --------------: |
| Component  | Local    | Actual         | —          | **1 criterion** |

**Coverage basis.** One below-one default tool-round partition is required; zero is the exact lower-bound counterexample.

**Representation basis.** The retained path executes the actual local configuration validation implementation; no material external surrogate or model participant is involved.

### Verification criteria

| Criterion                    | Contract                                      | Test level | Boundary | Required paths | Success criterion                                   |
| ---------------------------- | --------------------------------------------- | ---------- | -------- | -------------: | --------------------------------------------------- |
| `VC_CONFIG_TOOL_ROUND_LIMIT` | {need}`[[id]] <TREQ_CONFIG_TOOL_ROUND_LIMIT>` | Component  | Local    |              1 | A default tool-round maximum below one is rejected. |

### Evidence aggregation

| Signal                 | Rule | Applies to                                                         |
| ---------------------- | ---- | ------------------------------------------------------------------ |
| Semantic coverage      | ALL  | required verification criteria and each criterion's declared paths |
| Representation         | ALL  | retained evidence for satisfied criteria                           |
| Provenance             | ALL  | retained evidence for satisfied criteria; every required producer  |
| Freshness              | ALL  | retained evidence for satisfied criteria                           |
| Producer qualification | ALL  | retained evidence for satisfied criteria                           |
| M&S validation         | ALL  | applicable surrogate/model evidence                                |

### Fault applicability

| REQUIRED                                        | OPTIONAL | N/A                                                                                                                                                                                                            |
| ----------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `impl.comparison` · `impl.boundary`             | —        | `impl.control-flow` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.unexpected-interaction` · `interface.error-status` · `interface.payload-schema` |
| `spec.wrong-outcome` · `spec.missing-partition` | —        | `architecture.forbidden-edge` · `architecture.layer-bypass` · `spec.wrong-ordering-boundary`                                                                                                                   |

#### Fault-group rationale

| Group                 | Why                                                                               |
| --------------------- | --------------------------------------------------------------------------------- |
| Implementation        | The lower-bound comparison implements the default tool-loop budget constraint.    |
| Runtime / dependency  | Tool execution itself is outside validity of the configured default.              |
| Interface / protocol  | No tool/provider protocol interaction is required to validate the count.          |
| Architecture          | Internal topology is not normative.                                               |
| Specification / model | Accepting zero rounds or omitting that invalid partition violates the constraint. |

No blocking mutation threshold is selected.

(verification-profile-treq-config-structured-output-attempts)=

## Profile · TREQ_CONFIG_STRUCTURED_OUTPUT_ATTEMPTS

**Verification intent.** Prove the configured structured-output maximum-attempt count
is at least one.

**Models:** {ref}`Configuration validation <test-plan-configuration-validation-model>`

### Required coverage

| Test level | Boundary | Representation | M&S target |          Target |
| ---------- | -------- | -------------- | ---------- | --------------: |
| Component  | Local    | Actual         | —          | **1 criterion** |

**Coverage basis.** One below-one structured-output attempt partition is required; zero is the exact lower-bound counterexample.

**Representation basis.** The retained path executes the actual local configuration validation implementation; no material external surrogate or model participant is involved.

### Verification criteria

| Criterion                              | Contract                                                | Test level | Boundary | Required paths | Success criterion                                                |
| -------------------------------------- | ------------------------------------------------------- | ---------- | -------- | -------------: | ---------------------------------------------------------------- |
| `VC_CONFIG_STRUCTURED_OUTPUT_ATTEMPTS` | {need}`[[id]] <TREQ_CONFIG_STRUCTURED_OUTPUT_ATTEMPTS>` | Component  | Local    |              1 | A structured-output maximum-attempt count below one is rejected. |

### Evidence aggregation

| Signal                 | Rule | Applies to                                                         |
| ---------------------- | ---- | ------------------------------------------------------------------ |
| Semantic coverage      | ALL  | required verification criteria and each criterion's declared paths |
| Representation         | ALL  | retained evidence for satisfied criteria                           |
| Provenance             | ALL  | retained evidence for satisfied criteria; every required producer  |
| Freshness              | ALL  | retained evidence for satisfied criteria                           |
| Producer qualification | ALL  | retained evidence for satisfied criteria                           |
| M&S validation         | ALL  | applicable surrogate/model evidence                                |

### Fault applicability

| REQUIRED                                        | OPTIONAL | N/A                                                                                                                                                                                                            |
| ----------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `impl.comparison` · `impl.boundary`             | —        | `impl.control-flow` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.unexpected-interaction` · `interface.error-status` · `interface.payload-schema` |
| `spec.wrong-outcome` · `spec.missing-partition` | —        | `architecture.forbidden-edge` · `architecture.layer-bypass` · `spec.wrong-ordering-boundary`                                                                                                                   |

#### Fault-group rationale

| Group                 | Why                                                                                 |
| --------------------- | ----------------------------------------------------------------------------------- |
| Implementation        | The lower-bound comparison implements the configured repair-attempt constraint.     |
| Runtime / dependency  | Structured-output execution/repair runtime is outside this configuration invariant. |
| Interface / protocol  | Provider response shape is irrelevant to validity of the configured count.          |
| Architecture          | Internal topology is not normative.                                                 |
| Specification / model | Accepting zero attempts or omitting that invalid partition violates the constraint. |

No blocking mutation threshold is selected.

(verification-profile-treq-config-default-provider-declaration)=

## Profile · TREQ_CONFIG_DEFAULT_PROVIDER_DECLARATION

**Verification intent.** Prove that the configured default provider is present in the
effective provider catalog.

**Models:** {ref}`Configuration validation <test-plan-configuration-validation-model>`

### Required coverage

| Test level | Boundary | Representation | M&S target |          Target |
| ---------- | -------- | -------------- | ---------- | --------------: |
| Component  | Local    | Actual         | —          | **1 criterion** |

**Coverage basis.** One undeclared-default-provider partition is required because the TREQ has one catalog-membership obligation.

**Representation basis.** The retained path executes the actual local configuration validation implementation; no material external surrogate or model participant is involved.

### Verification criteria

| Criterion                                | Contract                                                  | Test level | Boundary | Required paths | Success criterion                                                |
| ---------------------------------------- | --------------------------------------------------------- | ---------- | -------- | -------------: | ---------------------------------------------------------------- |
| `VC_CONFIG_DEFAULT_PROVIDER_DECLARATION` | {need}`[[id]] <TREQ_CONFIG_DEFAULT_PROVIDER_DECLARATION>` | Component  | Local    |              1 | A default provider absent from the provider catalog is rejected. |

### Evidence aggregation

| Signal                 | Rule | Applies to                                                         |
| ---------------------- | ---- | ------------------------------------------------------------------ |
| Semantic coverage      | ALL  | required verification criteria and each criterion's declared paths |
| Representation         | ALL  | retained evidence for satisfied criteria                           |
| Provenance             | ALL  | retained evidence for satisfied criteria; every required producer  |
| Freshness              | ALL  | retained evidence for satisfied criteria                           |
| Producer qualification | ALL  | retained evidence for satisfied criteria                           |
| M&S validation         | ALL  | applicable surrogate/model evidence                                |

### Fault applicability

| REQUIRED                                        | OPTIONAL | N/A                                                                                                                                                                                                        |
| ----------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `impl.comparison` · `impl.control-flow`         | —        | `impl.boundary` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.unexpected-interaction` · `interface.error-status` · `interface.payload-schema` |
| `spec.wrong-outcome` · `spec.missing-partition` | —        | `architecture.forbidden-edge` · `architecture.layer-bypass` · `spec.wrong-ordering-boundary`                                                                                                               |

#### Fault-group rationale

| Group                 | Why                                                                                    |
| --------------------- | -------------------------------------------------------------------------------------- |
| Implementation        | Catalog-membership comparison and rejection control flow implement the rule.           |
| Runtime / dependency  | The declaration check is local and independent of provider availability.               |
| Interface / protocol  | No external protocol interaction is required.                                          |
| Architecture          | Internal topology is not normative.                                                    |
| Specification / model | Accepting an undeclared default provider or omitting that partition violates the rule. |

No blocking mutation threshold is selected.

(verification-profile-treq-config-default-model-mapping)=

## Profile · TREQ_CONFIG_DEFAULT_MODEL_MAPPING

**Verification intent.** Prove both independent default model/provider mapping
obligations: the default model must be declared and it must map to the default provider.

**Models:** {ref}`Configuration validation <test-plan-configuration-validation-model>`

### Required coverage

| Test level | Boundary | Representation | M&S target |          Target |
| ---------- | -------- | -------------- | ---------- | --------------: |
| Component  | Local    | Actual         | —          | **1 criterion** |

**Coverage basis.** Two independent partitions are required: default model absent from the registry and default model lacking a mapping for the declared default provider.

**Representation basis.** The retained path executes the actual local configuration validation implementation; no material external surrogate or model participant is involved.

### Verification criteria

| Criterion                         | Contract                                           | Test level | Boundary | Required paths | Required path IDs                                               | Success criterion                                                                         |
| --------------------------------- | -------------------------------------------------- | ---------- | -------- | -------------: | --------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| `VC_CONFIG_DEFAULT_MODEL_MAPPING` | {need}`[[id]] <TREQ_CONFIG_DEFAULT_MODEL_MAPPING>` | Component  | Local    |              2 | `default-model-undeclared` · `default-provider-mapping-missing` | Missing default-model declaration and missing default-provider mapping are both rejected. |

### Evidence aggregation

| Signal                 | Rule | Applies to                                                         |
| ---------------------- | ---- | ------------------------------------------------------------------ |
| Semantic coverage      | ALL  | required verification criteria and each criterion's declared paths |
| Representation         | ALL  | retained evidence for satisfied criteria                           |
| Provenance             | ALL  | retained evidence for satisfied criteria; every required producer  |
| Freshness              | ALL  | retained evidence for satisfied criteria                           |
| Producer qualification | ALL  | retained evidence for satisfied criteria                           |
| M&S validation         | ALL  | applicable surrogate/model evidence                                |

### Fault applicability

| REQUIRED                                        | OPTIONAL | N/A                                                                                                                                                                                                        |
| ----------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `impl.comparison` · `impl.control-flow`         | —        | `impl.boundary` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.unexpected-interaction` · `interface.error-status` · `interface.payload-schema` |
| `spec.wrong-outcome` · `spec.missing-partition` | —        | `architecture.forbidden-edge` · `architecture.layer-bypass` · `spec.wrong-ordering-boundary`                                                                                                               |

#### Fault-group rationale

| Group                 | Why                                                                                       |
| --------------------- | ----------------------------------------------------------------------------------------- |
| Implementation        | Registry membership and provider-mapping branches implement the two obligations.          |
| Runtime / dependency  | Model/provider execution is outside validity of the configured mapping.                   |
| Interface / protocol  | No external provider protocol is required to validate the mapping.                        |
| Architecture          | Internal topology is not normative.                                                       |
| Specification / model | Wrong acceptance or omission of either mapping partition violates the technical contract. |

No blocking mutation threshold is selected.

(verification-profile-treq-config-model-provider-references)=

## Profile · TREQ_CONFIG_MODEL_PROVIDER_REFERENCES

**Verification intent.** Prove every declared model has at least one provider mapping
and every referenced provider exists in the effective provider catalog.

**Models:** {ref}`Configuration validation <test-plan-configuration-validation-model>`

### Required coverage

| Test level | Boundary | Representation | M&S target |          Target |
| ---------- | -------- | -------------- | ---------- | --------------: |
| Component  | Local    | Actual         | —          | **1 criterion** |

**Coverage basis.** Two independent partitions are required: a model with no provider mapping and a mapping that references a provider absent from the catalog.

**Representation basis.** The retained path executes the actual local configuration validation implementation; no material external surrogate or model participant is involved.

### Verification criteria

| Criterion                             | Contract                                               | Test level | Boundary | Required paths | Required path IDs                                       | Success criterion                                                        |
| ------------------------------------- | ------------------------------------------------------ | ---------- | -------- | -------------: | ------------------------------------------------------- | ------------------------------------------------------------------------ |
| `VC_CONFIG_MODEL_PROVIDER_REFERENCES` | {need}`[[id]] <TREQ_CONFIG_MODEL_PROVIDER_REFERENCES>` | Component  | Local    |              2 | `empty-model-mapping` · `undeclared-provider-reference` | Empty mappings and references to undeclared providers are both rejected. |

### Evidence aggregation

| Signal                 | Rule | Applies to                                                         |
| ---------------------- | ---- | ------------------------------------------------------------------ |
| Semantic coverage      | ALL  | required verification criteria and each criterion's declared paths |
| Representation         | ALL  | retained evidence for satisfied criteria                           |
| Provenance             | ALL  | retained evidence for satisfied criteria; every required producer  |
| Freshness              | ALL  | retained evidence for satisfied criteria                           |
| Producer qualification | ALL  | retained evidence for satisfied criteria                           |
| M&S validation         | ALL  | applicable surrogate/model evidence                                |

### Fault applicability

| REQUIRED                                        | OPTIONAL | N/A                                                                                                                                                                                                        |
| ----------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `impl.comparison` · `impl.control-flow`         | —        | `impl.boundary` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.unexpected-interaction` · `interface.error-status` · `interface.payload-schema` |
| `spec.wrong-outcome` · `spec.missing-partition` | —        | `architecture.forbidden-edge` · `architecture.layer-bypass` · `spec.wrong-ordering-boundary`                                                                                                               |

#### Fault-group rationale

| Group                 | Why                                                                                       |
| --------------------- | ----------------------------------------------------------------------------------------- |
| Implementation        | Empty-mapping and dangling-reference branches implement the two required checks.          |
| Runtime / dependency  | Provider availability is irrelevant to local reference integrity.                         |
| Interface / protocol  | No provider interaction is needed to validate references.                                 |
| Architecture          | Internal topology is not normative.                                                       |
| Specification / model | Wrong acceptance or omission of either invalid reference partition violates the contract. |

No blocking mutation threshold is selected.
