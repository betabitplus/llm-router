(verification-profiles-developer)=

# Verification profiles · Developer usability

These profiles own verification design for {need}`GOAL_DEVELOPER_USABILITY`.
The public import contract and example-import safety remain normative Requirements;
this page defines the retained proof denominator.

(verification-profile-req-public-api-surface)=

## Profile · REQ_PUBLIC_API_SURFACE

**Verification intent.** Prove that the complete package-declared public surface
resolves from `llm_router` itself without requiring any caller-side internal-module
import.

**Models:** {ref}`Public package surface <test-plan-public-api-model>`

### Required coverage

| Test level | Boundary | Representation | M&S target |          Target |
| ---------- | -------- | -------------- | ---------- | --------------: |
| Component  | Local    | Actual         | —          | **1 criterion** |

**Coverage basis.** `llm_router.__all__` is the authoritative declared surface, so one
collection-level criterion checks every declared symbol in the current package.

**Representation basis.** The criterion imports and inspects the actual installed
`llm_router` package surface. No surrogate or external dependency represents the
public API under test.

### Verification criteria

| Criterion                    | Contract                                | Test level | Boundary | Required paths | Success criterion                                                                          |
| ---------------------------- | --------------------------------------- | ---------- | -------- | -------------: | ------------------------------------------------------------------------------------------ |
| `VC_PUBLIC_API_ROOT_EXPORTS` | {need}`[[id]] <REQ_PUBLIC_API_SURFACE>` | Component  | Local    |              1 | The declared surface is non-empty and every declared entry resolves from the package root. |

### Evidence aggregation

| Signal                 | Rule | Applies to                               |
| ---------------------- | ---- | ---------------------------------------- |
| Semantic coverage      | ALL  | required verification criteria and paths |
| Representation         | ALL  | retained evidence                        |
| Provenance             | ALL  | retained evidence                        |
| Producer qualification | ALL  | retained evidence                        |
| Freshness              | ALL  | retained evidence                        |
| M&S validation         | ALL  | applicable surrogate/model evidence      |

### Fault applicability

| REQUIRED                                                                      | OPTIONAL            | N/A                                                                                                                                                                                                                                                                                             |
| ----------------------------------------------------------------------------- | ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `architecture.layer-bypass` · `spec.wrong-outcome` · `spec.missing-partition` | `impl.control-flow` | `impl.comparison` · `impl.boundary` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.unexpected-interaction` · `interface.error-status` · `interface.payload-schema` · `architecture.forbidden-edge` · `spec.wrong-ordering-boundary` |

#### Fault-group rationale

| Group                 | Why                                                                                                     |
| --------------------- | ------------------------------------------------------------------------------------------------------- |
| Implementation        | Export assembly can fail through control flow, but numeric/operator boundaries are not meaningful here. |
| Runtime / dependency  | Root import resolution is local and dependency availability is not the contract.                        |
| Interface / protocol  | No external protocol is exercised.                                                                      |
| Architecture          | Requiring callers to bypass the package root is the explicit architectural failure mode.                |
| Specification / model | A missing declared symbol or wrong root resolution directly violates the Requirement.                   |

No blocking mutation threshold is selected; required deterministic fault classes remain
blocking.

(verification-profile-req-example-import-safety)=

## Profile · REQ_EXAMPLE_IMPORT_SAFETY

**Verification intent.** Import every shipped Python example independently under
network and live-router sentinels, forcing a fresh module execution for each example.

**Models:** {ref}`Executable example import safety <test-plan-example-import-safety-model>`

### Required coverage

| Test level | Boundary | Representation | M&S target |          Target |
| ---------- | -------- | -------------- | ---------- | --------------: |
| Component  | Local    | Actual         | —          | **1 criterion** |

**Coverage basis.** The denominator is every shipped `examples/llm_router/*.py` module
except `__init__.py`. The current source tree contains six such modules, so the single
criterion requires six retained parameterized paths.

**Representation basis.** Each path imports the actual shipped example module under
local network/live-workflow sentinels. No surrogate stands in for the example import
semantics being claimed.

### Verification criteria

| Criterion                  | Contract                                   | Test level | Boundary | Required paths | Required path IDs                                                                                                | Success criterion                                                                                           |
| -------------------------- | ------------------------------------------ | ---------- | -------- | -------------: | ---------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| `VC_EXAMPLE_IMPORT_SAFETY` | {need}`[[id]] <REQ_EXAMPLE_IMPORT_SAFETY>` | Component  | Local    |              6 | `key_rotation` · `multi_route` · `multimodal_inputs` · `session_workflow` · `structured_output` · `tool_calling` | Every shipped example executes a fresh import without network activity or invoking the live query workflow. |

### Evidence aggregation

| Signal                 | Rule | Applies to                                                 |
| ---------------------- | ---- | ---------------------------------------------------------- |
| Semantic coverage      | ALL  | required verification criterion and all six declared paths |
| Representation         | ALL  | retained evidence                                          |
| Provenance             | ALL  | retained evidence                                          |
| Producer qualification | ALL  | retained evidence                                          |
| Freshness              | ALL  | retained evidence                                          |
| M&S validation         | ALL  | applicable surrogate/model evidence                        |

### Fault applicability

| REQUIRED                                                                                                   | OPTIONAL | N/A                                                                                                                                                                                                                                                                                      |
| ---------------------------------------------------------------------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `impl.control-flow` · `interface.unexpected-interaction` · `spec.wrong-outcome` · `spec.missing-partition` | —        | `impl.comparison` · `impl.boundary` · `runtime.latency-timeout` · `runtime.unavailable-disconnect` · `runtime.malformed-response` · `interface.error-status` · `interface.payload-schema` · `architecture.forbidden-edge` · `architecture.layer-bypass` · `spec.wrong-ordering-boundary` |

#### Fault-group rationale

| Group                 | Why                                                                                                                      |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| Implementation        | The `__main__`/import control-flow guard is the primary implementation safety boundary.                                  |
| Runtime / dependency  | Import must not start a runtime dependency workflow at all, so dependency outcome classes are not the selected stimulus. |
| Interface / protocol  | Any network/live-router interaction during import is itself the forbidden interface event.                               |
| Architecture          | No internal dependency edge is prescribed.                                                                               |
| Specification / model | Executing a workflow or omitting one shipped example from verification invalidates the claim.                            |

No blocking mutation threshold is selected; required deterministic fault classes remain
blocking.
