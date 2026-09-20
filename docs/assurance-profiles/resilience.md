(assurance-profile-resilient-execution)=

# Assurance profile · Resilient execution

**Scope:** {need}`GOAL_RESILIENT_EXECUTION` and its direct Feature branches.

**Policy:** {ref}`Upper-level assurance and validation <test-plan-upper-level-assurance>`

This profile declares only cross-capability and Goal-outcome Targets that are not owned
by one Requirement or Technical requirement. Child-support gates come from the
authoritative Sphinx-Needs `derives` graph.

## Feature · FEAT_PROVIDER_RETRY

**Requirement support:** ALL direct Requirements deriving from
{need}`FEAT_PROVIDER_RETRY`.

### Capability integration

**Target:** N/A — the Feature currently has one direct Requirement, so there is no
cross-Requirement interaction to prove at this level.

### Capability validation

**Target:** N/A — the Feature claim is the same bounded provider-retry behavior already
owned by {need}`REQ_PROVIDER_RETRY` plus its Technical support. A second Feature-level
scenario would duplicate Requirement evidence.

## Feature · FEAT_STRUCTURED_RECOVERY

**Requirement support:** ALL direct Requirements deriving from
{need}`FEAT_STRUCTURED_RECOVERY`.

### Capability integration

**Target:** N/A — the Feature currently has one direct Requirement, so there is no
cross-Requirement interaction to prove at this level.

### Capability validation

**Target:** N/A — the Feature claim is the same bounded structured-output recovery
behavior already owned by {need}`REQ_STRUCTURED_OUTPUT_REPAIR` plus its Technical
support. A second Feature-level scenario would duplicate Requirement evidence.

## Goal · GOAL_RESILIENT_EXECUTION

**Capability support:** ALL direct Features deriving from
{need}`GOAL_RESILIENT_EXECUTION`.

### Cross-capability integration

| Criterion                            | Method     | Test level         | Boundary   | Representation | Required executions | Success criterion                                                                                                                                                                                            |
| ------------------------------------ | ---------- | ------------------ | ---------- | -------------- | ------------------: | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `AGI_RESILIENCE_RETRY_DURING_REPAIR` | pytest-bdd | System Integration | Substitute | Surrogate      |                   1 | After a schema-invalid response starts structured repair, a transient provider failure during the repair turn is retried on the same route and the later valid structured response is returned successfully. |

### Outcome validation

| Criterion                                | Method     | Test level         | Boundary   | Representation | Required executions | Success criterion                                                                                                                                                                                                                                   |
| ---------------------------------------- | ---------- | ------------------ | ---------- | -------------- | ------------------: | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `AOV_RESILIENCE_COMBINED_BUDGET_CEILING` | pytest-bdd | System Integration | Substitute | Surrogate      |                   1 | With provider retry maximum 2 and structured-output maximum 2, two structured attempts that each consume one transient retry stop after exactly four provider interactions; no fifth interaction occurs and the bounded public failure is returned. |
