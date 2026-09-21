(assurance-profile-rich-input-output)=

# Assurance profile · Rich input and structured output

**Scope:** {need}`GOAL_RICH_INPUT_OUTPUT` and
{need}`FEAT_STRUCTURED_OUTPUT`.

**Policy:** {ref}`Upper-level assurance and validation <test-plan-upper-level-assurance>`

This profile declares only cross-Requirement Targets that cannot be reduced to one
Requirement. Requirement coverage remains owned by the six direct Requirements and
their Verification Profiles.

## Feature · FEAT_STRUCTURED_OUTPUT

**Requirement support:** ALL direct Requirements deriving from
{need}`FEAT_STRUCTURED_OUTPUT`.

### Capability integration

| Criterion                          | Method     | Test level         | Boundary   | Representation | Required executions | Success criterion                                                                                                                                                                                                  |
| ---------------------------------- | ---------- | ------------------ | ---------- | -------------- | ------------------: | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `AC_RICH_SCHEMA_MEDIA_COMPOSITION` | pytest-bdd | System Integration | Substitute | Surrogate      |                   1 | One public request containing ordered text plus image content and a caller schema crosses the provider boundary with both media and schema semantics intact and returns the validated provider-independent result. |

### Capability validation

| Criterion                              | Method     | Test level | Boundary | Representation | Required executions | Success criterion                                                                                                                                    |
| -------------------------------------- | ---------- | ---------- | -------- | -------------- | ------------------: | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ACV_RICH_INVALID_SCHEMA_PRE_PROVIDER` | pytest-bdd | System     | Local    | Actual         |                   1 | A rich request containing valid media but an invalid caller schema is rejected during router-side normalization before any provider request is sent. |

## Goal · GOAL_RICH_INPUT_OUTPUT

**Capability support:** ALL direct Features deriving from
{need}`GOAL_RICH_INPUT_OUTPUT`.

### Cross-capability integration

**Target:** N/A — the Goal has one direct Feature, so there is no cross-Feature
interaction to prove at this level.

### Outcome validation

| Criterion                            | Method     | Test level         | Boundary   | Representation | Required executions | Success criterion                                                                                                                                                                                               |
| ------------------------------------ | ---------- | ------------------ | ---------- | -------------- | ------------------: | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `AOV_RICH_PROVIDER_SWAP_EQUIVALENCE` | pytest-bdd | System Integration | Substitute | Surrogate      |                   1 | The same caller image-and-schema intent executed through OpenAI-compatible and Google GenAI provider families returns the same schema-valid public structured meaning without provider-specific result leakage. |
