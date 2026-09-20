(assurance-profile-session-continuity)=

# Assurance profile · Session continuity

**Scope:** {need}`GOAL_SESSION_CONTINUITY` and its direct Feature branch.

**Policy:** {ref}`Upper-level assurance and validation <test-plan-upper-level-assurance>`

This profile declares only cross-Requirement and Goal-level Targets that are not owned by one Requirement or Technical requirement. Child-support gates come from the authoritative Sphinx-Needs `derives` graph.

## Feature · FEAT_SESSION_LIFECYCLE

**Requirement support:** ALL direct Requirements deriving from {need}`FEAT_SESSION_LIFECYCLE`.

### Capability integration

| Criterion                               | Method     | Test level            | Boundary | Representation | Required executions | Success criterion                                                                                                              |
| --------------------------------------- | ---------- | --------------------- | -------- | -------------- | ------------------: | ------------------------------------------------------------------------------------------------------------------------------ |
| `AC_SESSION_FORK_PERSISTENCE_ISOLATION` | pytest-bdd | Component Integration | Local    | Actual         |                   1 | A fork may diverge, be persisted, and be restored with its branch-specific history while the source session remains unchanged. |

### Capability validation

**Target:** N/A — the Feature has one coherent lifecycle/persistence capability. Its distinct cross-Requirement interaction is covered above; realistic resumed execution is owned by the Goal outcome instead of duplicating the same scenario at Feature level.

## Goal · GOAL_SESSION_CONTINUITY

**Capability support:** ALL direct Features deriving from {need}`GOAL_SESSION_CONTINUITY`.

### Cross-capability integration

**Target:** N/A — the Goal currently has one direct Feature, so there is no cross-Feature interaction to prove at this level.

### Outcome validation

| Criterion                         | Method     | Test level         | Boundary   | Representation | Required executions | Success criterion                                                                                                                                                                                                   |
| --------------------------------- | ---------- | ------------------ | ---------- | -------------- | ------------------: | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `AOV_SESSION_RESTORED_CONTINUITY` | pytest-bdd | System Integration | Substitute | Surrogate      |                   1 | A persisted session can be restored and attached to a new public router request; retained history reaches the provider before the new turn, the response is remembered, and an independent sibling stays unchanged. |
