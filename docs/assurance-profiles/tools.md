(assurance-profile-tool-orchestration)=

# Assurance profile · Tool orchestration

**Scope:** {need}`GOAL_TOOL_ORCHESTRATION` and its direct Feature branches.

**Policy:** {ref}`Upper-level assurance and validation <test-plan-upper-level-assurance>`

This profile declares only cross-Requirement, cross-capability, and Goal-outcome Targets
that are not owned by one Requirement or Technical requirement. Child-support gates come
from the authoritative Sphinx-Needs `derives` graph.

## Feature · FEAT_TOOL_SELECTION

**Requirement support:** ALL direct Requirements deriving from {need}`FEAT_TOOL_SELECTION`.

### Capability integration

**Target:** N/A — the Feature currently has one direct Requirement, so there is no
cross-Requirement interaction to prove at this level.

### Capability validation

**Target:** N/A — the Feature claim is the same explicit-selection behavior already owned
by {need}`REQ_TOOL_CHOICE`. A second Feature-level scenario would duplicate Requirement
evidence rather than validate a distinct intended-use claim.

## Feature · FEAT_TOOL_EXECUTION

**Requirement support:** ALL direct Requirements deriving from {need}`FEAT_TOOL_EXECUTION`.

### Capability integration

| Criterion                                | Method     | Test level         | Boundary   | Representation | Required executions | Success criterion                                                                                                                                                                       |
| ---------------------------------------- | ---------- | ------------------ | ---------- | -------------- | ------------------: | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `AC_TOOL_EXECUTION_SUCCESS_THEN_FAILURE` | pytest-bdd | System Integration | Substitute | Surrogate      |                   1 | One local tool round succeeds and its result reaches the next provider turn; a later local tool failure then surfaces publicly and stops execution before any additional provider turn. |

### Capability validation

**Target:** N/A — the Feature's distinct cross-Requirement interaction is covered above.
Whole-request intended-use behavior that also includes explicit tool selection is owned by
the Goal outcome instead of duplicating another execution scenario here.

## Goal · GOAL_TOOL_ORCHESTRATION

**Capability support:** ALL direct Features deriving from {need}`GOAL_TOOL_ORCHESTRATION`.

### Cross-capability integration

| Criterion                              | Method     | Test level         | Boundary   | Representation | Required executions | Success criterion                                                                                                                                                                       |
| -------------------------------------- | ---------- | ------------------ | ---------- | -------------- | ------------------: | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `AGI_TOOL_SELECTION_EXECUTION_HANDOFF` | pytest-bdd | System Integration | Substitute | Surrogate      |                   1 | A named tool selected through the public request is the only executed tool, and its concrete result is returned in the next provider turn before the final public response is produced. |

### Outcome validation

| Criterion                                    | Method     | Test level         | Boundary   | Representation | Required executions | Success criterion                                                                                                                                                                                                                        |
| -------------------------------------------- | ---------- | ------------------ | ---------- | -------------- | ------------------: | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `AOV_TOOL_ORCHESTRATION_BOUNDED_FORCED_LOOP` | pytest-bdd | System Integration | Substitute | Surrogate      |                   1 | Across a repeated tool-request workflow, the caller's explicit named choice remains enforced on every provider turn, only that tool executes, and the configured round limit terminates execution while preserving the outstanding call. |
