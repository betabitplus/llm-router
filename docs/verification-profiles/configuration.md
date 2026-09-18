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

| Criterion                        | Contract                                         | Test level         | Success criterion                                                                     |
| -------------------------------- | ------------------------------------------------ | ------------------ | ------------------------------------------------------------------------------------- |
| `VC_REQUEST_OMISSION_PROPERTY`   | {need}`[[id]] <REQ_REQUEST_OVERRIDE_PRECEDENCE>` | Component          | Generated combinations preserve omission as distinct from an explicit call value.     |
| `VC_REQUEST_OVERRIDE_PRECEDENCE` | {need}`[[id]] <REQ_REQUEST_OVERRIDE_PRECEDENCE>` | System Integration | Request settings override router and route defaults while unrelated defaults survive. |
| `VC_REQUEST_EXPLICIT_CLEAR`      | {need}`[[id]] <REQ_REQUEST_OVERRIDE_PRECEDENCE>` | System Integration | An explicit empty/null request value clears the inherited optional setting.           |

### Evidence aggregation

| Signal                 | Rule | Applies to                                                        |
| ---------------------- | ---- | ----------------------------------------------------------------- |
| Semantic coverage      | ALL  | required verification criteria                                    |
| Representation         | ALL  | retained evidence for satisfied criteria                          |
| Provenance             | ALL  | retained evidence for satisfied criteria                          |
| Producer qualification | ALL  | retained evidence for satisfied criteria; every required producer |
| Freshness              | ALL  | retained evidence for satisfied criteria                          |
| M&S validation         | ALL  | applicable surrogate/model evidence                               |

No fault classes or blocking mutation checks are selected for this profile.

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

**Coverage basis.** Component coverage owns the four key-source partitions. System coverage owns the
public missing-key error path.

**Representation basis.** All required paths execute the actual llm-router implementation and do not
depend on a material provider surrogate.

### Verification criteria

| Criterion                            | Contract                                   | Test level | Success criterion                                                                   |
| ------------------------------------ | ------------------------------------------ | ---------- | ----------------------------------------------------------------------------------- |
| `VC_CREDENTIAL_CUSTOM_ENV_NAME`      | {need}`[[id]] <REQ_CREDENTIAL_RESOLUTION>` | Component  | A configured fixed key resolves through its configured custom environment name.     |
| `VC_CREDENTIAL_AUTO_ROTATION`        | {need}`[[id]] <REQ_CREDENTIAL_RESOLUTION>` | Component  | Automatic key selection rotates deterministically over sorted available key IDs.    |
| `VC_CREDENTIAL_REQUIRED_MISSING`     | {need}`[[id]] <REQ_CREDENTIAL_RESOLUTION>` | Component  | A missing required credential raises the public missing-key error with identity.    |
| `VC_CREDENTIAL_OPTIONAL_MISSING`     | {need}`[[id]] <REQ_CREDENTIAL_RESOLUTION>` | Component  | An optional provider credential may resolve to the permitted empty bearer value.    |
| `VC_CREDENTIAL_PUBLIC_MISSING_ERROR` | {need}`[[id]] <REQ_CREDENTIAL_RESOLUTION>` | System     | A public request with a missing required credential surfaces the missing-key error. |

### Evidence aggregation

| Signal                 | Rule | Applies to                                                        |
| ---------------------- | ---- | ----------------------------------------------------------------- |
| Semantic coverage      | ALL  | required verification criteria                                    |
| Representation         | ALL  | retained evidence for satisfied criteria                          |
| Provenance             | ALL  | retained evidence for satisfied criteria                          |
| Producer qualification | ALL  | retained evidence for satisfied criteria; every required producer |
| Freshness              | ALL  | retained evidence for satisfied criteria                          |
| M&S validation         | ALL  | applicable surrogate/model evidence                               |

No fault classes or blocking mutation checks are selected for this profile.

(verification-profile-req-config-installation-coherence)=

## Profile · REQ_CONFIG_INSTALLATION_COHERENCE

**Verification intent.** Install a distinct replacement snapshot through the public configuration
API, prove that subsequent runtime construction captures that replacement snapshot, and directly
verify the derived cache-invalidation contract that prevents stale provider objects from surviving
the transition.

**Models:** {ref}`Configuration activation <test-plan-config-activation-model>`

### Required coverage

| Test level | Boundary | Representation | M&S target |         Target |
| ---------- | -------- | -------------- | ---------- | -------------: |
| Component  | Local    | Actual         | —          | **3 criteria** |

**Coverage basis.** The Component cell requires public replacement round-trip, runtime snapshot
capture, and the derived cache-invalidation criterion.

**Representation basis.** Every required path executes the actual llm-router implementation without
a material external surrogate.

### Verification criteria

| Criterion                                | Contract                                           | Test level | Success criterion                                                                                |
| ---------------------------------------- | -------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------ |
| `VC_CONFIG_INSTALLATION_ROUND_TRIP`      | {need}`[[id]] <REQ_CONFIG_INSTALLATION_COHERENCE>` | Component  | Installing a distinct valid snapshot makes that exact snapshot active via public API.            |
| `VC_CONFIG_INSTALLATION_RUNTIME_CAPTURE` | {need}`[[id]] <REQ_CONFIG_INSTALLATION_COHERENCE>` | Component  | Runtime construction after installation captures the newly active snapshot.                      |
| `VC_CONFIG_CACHE_INVALIDATION`           | {need}`[[id]] <TREQ_CONFIG_CACHE_INVALIDATION>`    | Component  | Installing a replacement configuration clears registered configuration-dependent adapter caches. |

### Evidence aggregation

| Signal                 | Rule | Applies to                                                        |
| ---------------------- | ---- | ----------------------------------------------------------------- |
| Semantic coverage      | ALL  | required verification criteria                                    |
| Representation         | ALL  | retained evidence for satisfied criteria                          |
| Provenance             | ALL  | retained evidence for satisfied criteria                          |
| Producer qualification | ALL  | retained evidence for satisfied criteria; every required producer |
| Freshness              | ALL  | retained evidence for satisfied criteria                          |
| M&S validation         | ALL  | applicable surrogate/model evidence                               |

No fault classes or blocking mutation checks are selected for this profile.
