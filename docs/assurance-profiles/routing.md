(assurance-profile-routing-reliability)=

# Assurance profile · Routing reliability

**Scope:** {need}`GOAL_ROUTING_RELIABILITY` and its direct Feature branches.

**Policy:** {ref}`Upper-level assurance and validation <test-plan-upper-level-assurance>`

This profile declares Targets before execution. Child-support gates are derived from the authoritative Sphinx-Needs `derives` graph; they are not duplicated here as a second hierarchy.

## Feature · FEAT_ROUTE_FALLBACK

**Requirement support:** ALL direct Requirements deriving from {need}`FEAT_ROUTE_FALLBACK`.

### Capability integration

| Criterion                            | Method     | Test level         | Boundary   | Representation | Required executions | Success criterion                                                                                                                                          |
| ------------------------------------ | ---------- | ------------------ | ---------- | -------------- | ------------------: | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `AC_ROUTE_FALLBACK_MULTI_HOP_STICKY` | pytest-bdd | System Integration | Substitute | Surrogate      |                   1 | After two failed routes, the third eligible route succeeds and becomes the next starting route without an earlier route being retried on the next request. |

### Capability validation

| Criterion                             | Method     | Test level         | Boundary   | Representation | Required executions | Success criterion                                                                                                                                                             |
| ------------------------------------- | ---------- | ------------------ | ---------- | -------------- | ------------------: | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ACV_ROUTE_FALLBACK_BOUNDED_RECOVERY` | pytest-bdd | System Integration | Substitute | Surrogate      |                   1 | Under a degraded four-route configuration, two failures are tolerated, the third route satisfies the request, and no route beyond the configured attempt budget is contacted. |

## Feature · FEAT_RATE_LIMIT_ROUTING

**Requirement support:** ALL direct Requirements deriving from {need}`FEAT_RATE_LIMIT_ROUTING`.

### Capability integration

**Target:** N/A — the Feature currently has one direct Requirement, so there is no cross-Requirement interaction to prove at this level.

### Capability validation

**Target:** N/A — no capability-level intended-use validation Target beyond the current Requirement contract is declared yet. The section remains reserved for a future distinct validation claim rather than duplicating Requirement evidence.

## Goal · GOAL_ROUTING_RELIABILITY

**Capability support:** ALL direct Features deriving from {need}`GOAL_ROUTING_RELIABILITY`.

### Cross-capability integration

| Criterion                           | Method     | Test level         | Boundary   | Representation | Required executions | Success criterion                                                                                                                                                         |
| ----------------------------------- | ---------- | ------------------ | ---------- | -------------- | ------------------: | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `AGI_ROUTING_BLOCKED_THEN_FALLBACK` | pytest-bdd | System Integration | Substitute | Surrogate      |                   1 | A locally blocked preferred route is not sent to the provider; the next eligible route may fail normally; routing then continues to a later eligible route that succeeds. |

### Outcome validation

| Criterion                          | Method     | Test level         | Boundary   | Representation | Required executions | Success criterion                                                                                                                                                                                             |
| ---------------------------------- | ---------- | ------------------ | ---------- | -------------- | ------------------: | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `AOV_ROUTING_PREDICTABLE_PROGRESS` | pytest-bdd | System Integration | Substitute | Surrogate      |                   1 | Across consecutive requests in a degraded route set, a request still succeeds through an eligible route and the recovered successful route becomes the preferred starting point once availability permits it. |
