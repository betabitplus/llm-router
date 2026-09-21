(assurance-profile-configuration-predictability)=

# Assurance profile · Configuration predictability

**Scope:** {need}`GOAL_CONFIGURATION_PREDICTABILITY` and
{need}`FEAT_CONFIGURATION_PRECEDENCE`.

**Policy:** {ref}`Upper-level assurance and validation <test-plan-upper-level-assurance>`

This profile declares only cross-Requirement Targets that cannot be reduced to one
Requirement or Technical requirement. Child-support gates come from the authoritative
Sphinx-Needs `derives` graph.

## Feature · FEAT_CONFIGURATION_PRECEDENCE

**Requirement support:** ALL direct Requirements deriving from
{need}`FEAT_CONFIGURATION_PRECEDENCE`.

### Capability integration

| Criterion                                     | Method     | Test level         | Boundary   | Representation | Required executions | Success criterion                                                                                                                                                                                               |
| --------------------------------------------- | ---------- | ------------------ | ---------- | -------------- | ------------------: | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `AC_CONFIGURATION_EFFECTIVE_VIEW_COMPOSITION` | pytest-bdd | System Integration | Substitute | Surrogate      |                   1 | After installing a replacement configuration, one public request uses the replacement credential, the explicit call override wins over router/route defaults, and an unrelated route default remains effective. |

### Capability validation

| Criterion                                  | Method     | Test level | Boundary | Representation | Required executions | Success criterion                                                                                                                                                                                                   |
| ------------------------------------------ | ---------- | ---------- | -------- | -------------- | ------------------: | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ACV_CONFIGURATION_POST_INSTALL_REJECTION` | pytest-bdd | System     | Local    | Actual         |                   1 | After a valid replacement configuration is installed, an unknown-model public request still fails as ConfigurationError before provider execution, sends zero provider requests, and leaves the replacement active. |

## Goal · GOAL_CONFIGURATION_PREDICTABILITY

**Capability support:** ALL direct Features deriving from
{need}`GOAL_CONFIGURATION_PREDICTABILITY`.

### Cross-capability integration

**Target:** N/A — the Goal currently has one direct Feature, so there is no cross-Feature
interaction to prove at this level.

### Outcome validation

**Target:** N/A — the Goal's caller-visible predictability claim is fully represented by
the Feature's cross-Requirement composition and post-install rejection validation above.
A separate Goal-level scenario would duplicate the same intended-use outcome.
