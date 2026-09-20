(assurance-profile-provider-portability)=

# Assurance profile · Provider portability

**Scope:** {need}`GOAL_PROVIDER_PORTABILITY` and its direct Feature branches.

**Policy:** {ref}`Upper-level assurance and validation <test-plan-upper-level-assurance>`

This profile declares only cross-Requirement, cross-capability, and Goal-outcome Targets
that are not owned by one Requirement or Technical requirement. Child-support gates come
from the authoritative Sphinx-Needs `derives` graph.

## Feature · FEAT_PROVIDER_INTEROPERABILITY

**Requirement support:** ALL direct Requirements deriving from
{need}`FEAT_PROVIDER_INTEROPERABILITY`.

### Capability integration

**Target:** N/A — the Feature currently has one direct Requirement, so there is no
cross-Requirement interaction to prove at this level.

### Capability validation

**Target:** N/A — the Feature claim is the same provider-family interoperability outcome
owned by {need}`REQ_PROVIDER_ADAPTER_INTEROPERABILITY` plus its five adapter Technical
requirements. A second Feature-level scenario would duplicate that proof.

## Feature · FEAT_ASYNC_EXECUTION

**Requirement support:** ALL direct Requirements deriving from
{need}`FEAT_ASYNC_EXECUTION`.

### Capability integration

**Target:** N/A — the Feature currently has one direct Requirement, so there is no
cross-Requirement interaction to prove at this level.

### Capability validation

**Target:** N/A — the Feature claim is the same async provider/capability matrix owned by
{need}`REQ_ASYNC_PROVIDER_EXECUTION`. A second Feature-level matrix would duplicate the
Requirement target.

## Feature · FEAT_PUBLIC_RESPONSE_CONTRACT

**Requirement support:** ALL direct Requirements deriving from
{need}`FEAT_PUBLIC_RESPONSE_CONTRACT`.

### Capability integration

| Criterion                                    | Method     | Test level         | Boundary   | Representation | Required executions | Success criterion                                                                                                                                                                                           |
| -------------------------------------------- | ---------- | ------------------ | ---------- | -------------- | ------------------: | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `AC_PROVIDER_PUBLIC_SUCCESS_ERROR_STABILITY` | pytest-bdd | System Integration | Substitute | Surrogate      |                   1 | Through one public provider route, a normalized successful response is returned first; a later provider rejection then surfaces as public ProviderError without leaking the provider-private error message. |

### Capability validation

**Target:** N/A — the Feature's distinct cross-Requirement interaction is covered by the
success/error integration target above.

## Goal · GOAL_PROVIDER_PORTABILITY

**Capability support:** ALL direct Features deriving from
{need}`GOAL_PROVIDER_PORTABILITY`.

### Cross-capability integration

| Criterion                                  | Method     | Test level         | Boundary   | Representation | Required executions | Success criterion                                                                                                                                                                                                  |
| ------------------------------------------ | ---------- | ------------------ | ---------- | -------------- | ------------------: | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `AGI_PROVIDER_SYNC_ASYNC_SWAP_EQUIVALENCE` | pytest-bdd | System Integration | Substitute | Surrogate      |                   1 | The same semantic text result returned synchronously through OpenAI-compatible and asynchronously through Google GenAI preserves the same public success meaning while crossing two different provider boundaries. |

### Outcome validation

| Criterion                                              | Method     | Test level         | Boundary   | Representation | Required executions | Success criterion                                                                                                                                                                                                                                          |
| ------------------------------------------------------ | ---------- | ------------------ | ---------- | -------------- | ------------------: | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `AOV_PROVIDER_SWAP_PRESERVES_SUCCESS_FAILURE_CONTRACT` | pytest-bdd | System Integration | Substitute | Surrogate      |                   1 | After a successful OpenAI-compatible request and an equivalent asynchronous Google GenAI request, a later Google provider rejection still surfaces as public ProviderError, preserves one provider interaction, and does not leak provider-private detail. |
