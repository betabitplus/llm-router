(verification-profiles-configuration)=

# Verification profiles · Configuration

These profiles own verification design for the remaining parent contracts in
{need}`FEAT_CONFIGURATION_PRECEDENCE`. Product semantics stay in the normative
Requirements and Technical requirements; the profiles below select stable
verification criteria and the evidence paths required to demonstrate them.

(verification-profile-req-request-override-precedence)=

## Profile · REQ_REQUEST_OVERRIDE_PRECEDENCE

**Verification intent.** Exercise competing router, route, and request values through the public
configuration path, prove explicit clearing at the provider-facing request boundary, and use
property-based coverage to distinguish omission from an explicitly supplied value across generated
combinations.

**Models:** {ref}`Configuration precedence <test-plan-configuration-precedence-model>`

### Required coverage

| Test level         | Boundary   | Representation | M&S target |          Target |
| ------------------ | ---------- | -------------- | ---------- | --------------: |
| Component          | Local      | Actual         | —          | **1 criterion** |
| System Integration | Substitute | Surrogate      | L0         |  **2 criteria** |

**Coverage basis.** Component coverage proves generated omission-vs-explicit-value semantics.
System-integration coverage proves public override and explicit-clear behavior while observing the
request sent across the configured provider HTTP boundary.

**Representation basis.** The Component path executes the actual llm-router implementation without
a material external surrogate. The System-integration paths execute actual llm-router code but use
the qualified scripted HTTP provider as a surrogate external participant; L0 is sufficient because
the verification claim is the request constructed by llm-router, not fidelity of provider behavior.

### Verification criteria

| Criterion                        | Contract                                         | Test level         | Boundary   | Required paths | Required path IDs           | Success criterion                                                                                                   |
| -------------------------------- | ------------------------------------------------ | ------------------ | ---------- | -------------: | --------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `VC_REQUEST_OMISSION_PROPERTY`   | {need}`[[id]] <REQ_REQUEST_OVERRIDE_PRECEDENCE>` | Component          | Local      |              1 | —                           | Generated combinations preserve omission as distinct from an explicit call value.                                   |
| `VC_REQUEST_OVERRIDE_PRECEDENCE` | {need}`[[id]] <REQ_REQUEST_OVERRIDE_PRECEDENCE>` | System Integration | Substitute |              1 | —                           | Request settings override router and route defaults while unrelated defaults survive.                               |
| `VC_REQUEST_EXPLICIT_CLEAR`      | {need}`[[id]] <REQ_REQUEST_OVERRIDE_PRECEDENCE>` | System Integration | Substitute |              2 | `null` · `empty-collection` | Explicit null and explicit empty-collection request values each clear the corresponding inherited optional setting. |

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

| REQUIRED                                                                         | OPTIONAL | N/A                                                                                                                         |
| -------------------------------------------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------------- |
| `impl.comparison` · `impl.boundary` · `impl.control-flow`                        | —        | `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response`                                 |
| `interface.payload-schema`                                                       | —        | `interface.unexpected-interaction` · `interface.error-status` · `architecture.forbidden-edge` · `architecture.layer-bypass` |
| `spec.wrong-outcome` · `spec.missing-partition` · `spec.wrong-ordering-boundary` | —        | —                                                                                                                           |

#### Fault-group rationale

| Group                 | Why                                                                                                                     |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| Implementation        | Layer precedence and explicit-null handling are implemented by branch/boundary decisions that must not silently invert. |
| Runtime / dependency  | Provider availability, latency, and malformed replies do not determine which local configuration value is effective.    |
| Interface / protocol  | The provider-facing payload must preserve the resolved value/omission semantics; provider status behavior is separate.  |
| Architecture          | This Requirement does not depend on a particular internal layering topology.                                            |
| Specification / model | Ordering, omission-vs-explicit partitions, and the resulting value are the contract itself.                             |

No blocking mutation threshold is selected; the required deterministic fault classes remain blocking.

(verification-profile-req-credential-resolution)=

## Profile · REQ_CREDENTIAL_RESOLUTION

**Verification intent.** Directly verify the credential-source partitions named by the Requirement
and retain one public-system path proving that a missing required credential crosses the stable
public error boundary.

**Models:** {ref}`Credential resolution <test-plan-credential-resolution-model>`

### Required coverage

| Test level | Boundary | Representation | M&S target |          Target |
| ---------- | -------- | -------------- | ---------- | --------------: |
| Component  | Local    | Actual         | —          |  **4 criteria** |
| System     | Local    | Actual         | —          | **1 criterion** |

**Coverage basis.** Component coverage owns the four key-source partitions. Automatic rotation
requires both configured custom-key mappings and convention-discovered environment keys. The
optional-missing criterion requires one retained path for every provider family that the implementation
explicitly permits to run without a bearer credential; that denominator is currently QwenChat +
Gemini WebAPI (2 paths). System coverage owns the public missing-key error path.

**Representation basis.** All required paths execute the actual llm-router implementation and do not
depend on a material provider surrogate.

### Verification criteria

| Criterion                            | Contract                                   | Test level | Boundary | Required paths | Required path IDs                                       | Success criterion                                                                                                       |
| ------------------------------------ | ------------------------------------------ | ---------- | -------- | -------------: | ------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `VC_CREDENTIAL_CUSTOM_ENV_NAME`      | {need}`[[id]] <REQ_CREDENTIAL_RESOLUTION>` | Component  | Local    |              1 | —                                                       | A configured fixed key resolves through its configured custom environment name.                                         |
| `VC_CREDENTIAL_AUTO_ROTATION`        | {need}`[[id]] <REQ_CREDENTIAL_RESOLUTION>` | Component  | Local    |              2 | `convention-discovered-keys` · `configured-custom-keys` | Automatic key selection rotates deterministically for configured custom-key mappings and convention-discovered key IDs. |
| `VC_CREDENTIAL_REQUIRED_MISSING`     | {need}`[[id]] <REQ_CREDENTIAL_RESOLUTION>` | Component  | Local    |              1 | —                                                       | A missing required credential raises the public missing-key error with identity.                                        |
| `VC_CREDENTIAL_OPTIONAL_MISSING`     | {need}`[[id]] <REQ_CREDENTIAL_RESOLUTION>` | Component  | Local    |              2 | `QwenChat` · `Gemini WebAPI`                            | Every provider family that permits an absent bearer credential resolves the permitted empty value.                      |
| `VC_CREDENTIAL_PUBLIC_MISSING_ERROR` | {need}`[[id]] <REQ_CREDENTIAL_RESOLUTION>` | System     | Local    |              1 | —                                                       | A public request with a missing required credential surfaces the missing-key error.                                     |

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

| REQUIRED                                                                         | OPTIONAL | N/A                                                                                                                                                      |
| -------------------------------------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `impl.comparison` · `impl.boundary` · `impl.control-flow`                        | —        | `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response`                                                              |
| `spec.wrong-outcome` · `spec.missing-partition` · `spec.wrong-ordering-boundary` | —        | `interface.unexpected-interaction` · `interface.error-status` · `interface.payload-schema` · `architecture.forbidden-edge` · `architecture.layer-bypass` |

#### Fault-group rationale

| Group                 | Why                                                                                                                     |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| Implementation        | Required/optional, fixed/auto, custom-name, and rotation branches can fail independently and must remain discriminated. |
| Runtime / dependency  | Credential resolution reads local configuration/environment state; remote dependency failure is outside this contract.  |
| Interface / protocol  | Provider protocol behavior is not part of credential-source selection or missing-key translation.                       |
| Architecture          | No internal layering topology is part of the credential-resolution contract.                                            |
| Specification / model | Source partitions, deterministic rotation ordering, and public missing-key outcome are all normative semantics.         |

No blocking mutation threshold is selected; the required deterministic fault classes remain blocking.

(verification-profile-req-config-installation-coherence)=

## Profile · REQ_CONFIG_INSTALLATION_COHERENCE

**Verification intent.** Install a distinct replacement snapshot through the public
configuration API, prove that subsequent runtime construction captures that replacement,
and prove a real post-install request observes replacement-derived behavior. Cache
invalidation is owned separately by the derived Technical requirement.

**Models:** {ref}`Configuration activation <test-plan-config-activation-model>`

### Required coverage

| Test level         | Boundary   | Representation | M&S target |          Target |
| ------------------ | ---------- | -------------- | ---------- | --------------: |
| Component          | Local      | Actual         | —          |  **2 criteria** |
| System Integration | Substitute | Surrogate      | L0         | **1 criterion** |

**Coverage basis.** Component coverage requires public replacement round-trip and
post-install runtime snapshot capture. System-integration coverage proves that a request
constructed after installation exhibits replacement-derived behavior at the provider
observation boundary. Cache invalidation has its own Technical-requirement denominator.

**Representation basis.** Component paths execute the actual llm-router implementation.
The System-integration path uses a scripted provider only as an observation boundary for
the replacement-derived request, so Surrogate/L0 is sufficient.

### Verification criteria

| Criterion                                | Contract                                           | Test level         | Boundary   | Required paths | Success criterion                                                                                          |
| ---------------------------------------- | -------------------------------------------------- | ------------------ | ---------- | -------------: | ---------------------------------------------------------------------------------------------------------- |
| `VC_CONFIG_INSTALLATION_ROUND_TRIP`      | {need}`[[id]] <REQ_CONFIG_INSTALLATION_COHERENCE>` | Component          | Local      |              1 | Installing a distinct valid snapshot makes that exact snapshot active via public API.                      |
| `VC_CONFIG_INSTALLATION_RUNTIME_CAPTURE` | {need}`[[id]] <REQ_CONFIG_INSTALLATION_COHERENCE>` | Component          | Local      |              1 | Runtime construction after installation captures the newly active snapshot.                                |
| `VC_CONFIG_INSTALLATION_RUNTIME_EFFECT`  | {need}`[[id]] <REQ_CONFIG_INSTALLATION_COHERENCE>` | System Integration | Substitute |              1 | A public request created after installation exhibits a replacement-derived value at the provider boundary. |

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

| Technical requirement                                                                   | Target |
| --------------------------------------------------------------------------------------- | ------ |
| {need}`Configuration-dependent caches are invalidated <TREQ_CONFIG_CACHE_INVALIDATION>` | PASS   |

### Fault applicability

| REQUIRED                                                                         | OPTIONAL | N/A                                                                                                                               |
| -------------------------------------------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `impl.control-flow`                                                              | —        | `impl.comparison` · `impl.boundary` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` |
| `architecture.layer-bypass`                                                      | —        | `interface.unexpected-interaction` · `interface.error-status` · `interface.payload-schema` · `architecture.forbidden-edge`        |
| `spec.wrong-outcome` · `spec.missing-partition` · `spec.wrong-ordering-boundary` | —        | —                                                                                                                                 |

#### Fault-group rationale

| Group                 | Why                                                                                                                |
| --------------------- | ------------------------------------------------------------------------------------------------------------------ |
| Implementation        | Installation must perform the active-state replacement and subsequent runtime capture rather than returning early. |
| Runtime / dependency  | Remote dependency behavior is not needed to prove that replacement configuration becomes locally effective.        |
| Interface / protocol  | The provider boundary is only an observation point; provider protocol failures are outside this contract.          |
| Architecture          | Bypassing the required configuration-state transition can leave subsequent runtime construction on stale state.    |
| Specification / model | Distinct replacement, post-install ordering, and observable runtime effect are normative state semantics.          |

No blocking mutation threshold is selected.

(verification-profile-treq-config-cache-invalidation)=

## Profile · TREQ_CONFIG_CACHE_INVALIDATION

**Verification intent.** Prove that installing a replacement active configuration
invalidates registered adapter caches whose values depend on configuration-derived
state.

**Models:** {ref}`Configuration activation <test-plan-config-activation-model>`

### Required coverage

| Test level | Boundary | Representation | M&S target |          Target |
| ---------- | -------- | -------------- | ---------- | --------------: |
| Component  | Local    | Actual         | —          | **1 criterion** |

**Coverage basis.** Cache invalidation is one direct technical side-effect obligation
independent of public configuration round-trip and runtime-observation evidence.

**Representation basis.** The retained test executes actual install_config and the real
registered cache invalidation mechanism locally.

### Verification criteria

| Criterion                      | Contract                                        | Test level | Boundary | Required paths | Success criterion                                                                                |
| ------------------------------ | ----------------------------------------------- | ---------- | -------- | -------------: | ------------------------------------------------------------------------------------------------ |
| `VC_CONFIG_CACHE_INVALIDATION` | {need}`[[id]] <TREQ_CONFIG_CACHE_INVALIDATION>` | Component  | Local    |              1 | Installing a replacement configuration clears registered configuration-dependent adapter caches. |

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

| REQUIRED                                                                         | OPTIONAL | N/A                                                                                                                                                                                                                            |
| -------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `impl.control-flow` · `architecture.layer-bypass`                                | —        | `impl.comparison` · `impl.boundary` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.unexpected-interaction` · `interface.error-status` · `interface.payload-schema` |
| `spec.wrong-outcome` · `spec.missing-partition` · `spec.wrong-ordering-boundary` | —        | `architecture.forbidden-edge`                                                                                                                                                                                                  |

#### Fault-group rationale

| Group                 | Why                                                                                                    |
| --------------------- | ------------------------------------------------------------------------------------------------------ |
| Implementation        | Skipping the registered invalidation callbacks leaves stale adapter instances reachable.               |
| Runtime / dependency  | Cache invalidation is a local state transition independent of provider runtime behavior.               |
| Interface / protocol  | No provider protocol interaction is required to invalidate local caches.                               |
| Architecture          | Bypassing the registered cache-invalidation transition can preserve configuration-derived stale state. |
| Specification / model | Missing invalidation, wrong post-install state, or wrong transition ordering violates the TREQ.        |

No blocking mutation threshold is selected.
