# Routing requirements

```{goal} Preserve request progress across route failures
:id: GOAL_ROUTING_RELIABILITY

Routing should continue predictably when another eligible route can satisfy a request after an earlier route fails or is temporarily unavailable.
```

```{feature} Route fallback
:id: FEAT_ROUTE_FALLBACK
:derives: GOAL_ROUTING_RELIABILITY

The router can move between eligible routes while respecting timeout, attempt-count, and subsequent-start policies.
```

```{req} Synchronous failed-route fallback
:id: REQ_SYNC_ROUTE_FALLBACK
:status: accepted
:revision: 1
:required_evidence: impl;bdd
:derives: FEAT_ROUTE_FALLBACK

**Statement.** During a synchronous request, when an attempted route fails before producing a successful response and another eligible route remains, the router shall continue with the next route. A successful result shall expose routing trace entries for both the failed attempt and the route that ultimately succeeded.

**Rationale.** A transient failure on one route should not turn into a user-visible request failure when another configured route can still satisfy the request, and the caller needs enough trace information to explain the fallback.

**Verification intent.** Exercise the public synchronous router with an initial failing route followed by a successful route and verify both the returned result and the observable routing trace.
```

```{req} Route timeout fallback
:id: REQ_ROUTE_TIMEOUT_FALLBACK
:status: accepted
:revision: 1
:required_evidence: impl;bdd
:derives: FEAT_ROUTE_FALLBACK

**Statement.** An attempt timeout shall stop waiting on the current route, continue to another eligible route when one remains, and surface a timeout error when no fallback remains.

**Rationale.** A slow or stalled provider must not consume the whole request indefinitely or prevent another eligible route from making progress.

**Verification intent.** Exercise the public router against a route that exceeds the configured attempt timeout and verify both fallback behavior and the terminal timeout behavior when no alternative remains.
```

```{req} Route attempt limit
:id: REQ_ROUTE_ATTEMPT_LIMIT
:status: accepted
:revision: 1
:required_evidence: impl;bdd
:derives: FEAT_ROUTE_FALLBACK

**Statement.** A request shall never attempt more routes than the configured route-attempt limit.

**Rationale.** Fallback must remain bounded so that a failing request cannot fan out across an uncontrolled number of providers or keys.

**Verification intent.** Execute a request with more eligible failing routes than the configured limit and verify the observable attempt count never exceeds that limit.
```

```{req} Successful route becomes the next starting route
:id: REQ_ROUTE_STICKY_START
:status: accepted
:revision: 1
:required_evidence: impl;bdd
:derives: FEAT_ROUTE_FALLBACK

**Statement.** After fallback succeeds, the next request through the same router shall begin from the route that most recently succeeded.

**Rationale.** Reusing the most recently successful route avoids repeatedly paying for a known failing first attempt while preserving the configured route set.

**Verification intent.** Drive one public request through fallback, issue a second request through the same router, and verify from the routing trace that the previously successful route is attempted first.
```

```{treq} Stable route ordering
:id: TREQ_ROUTE_ORDER
:status: accepted
:revision: 1
:required_evidence: impl;unit
:derives: REQ_ROUTE_STICKY_START

**Constraint.** Route ordering shall rotate or shuffle attempt order without losing the selected starting-route identity.

**Rationale.** Sticky-start behavior depends on stable route identity even when the candidate order is transformed internally.

**Verification intent.** Verify the route-ordering component directly with reordered candidate sets and assert that the selected starting route remains identifiable and correctly positioned.
```

```{feature} Rate-limit-aware routing
:id: FEAT_RATE_LIMIT_ROUTING
:derives: GOAL_ROUTING_RELIABILITY

Routing accounts for per-provider and per-key availability before choosing or waiting for an attempt.
```

```{req} Rate-limit-aware route and key selection
:id: REQ_RATE_LIMIT_ROUTING
:status: accepted
:revision: 1
:required_evidence: impl;bdd
:derives: FEAT_RATE_LIMIT_ROUTING

**Statement.** Blocked routes shall be skipped when another route is available. When all routes are blocked, the router shall fail immediately or wait according to configured policy. Available credentials shall rotate before reuse requires waiting.

**Rationale.** Rate-limit state should guide routing decisions rather than turning an otherwise serviceable request into unnecessary delay or failure.

**Verification intent.** Exercise the public router with observable blocked and available route/key states and verify route skipping, key rotation, and the configured all-blocked policy.
```

```{treq} Isolated limiter state
:id: TREQ_RATE_LIMIT_STATE
:status: accepted
:revision: 1
:required_evidence: impl;unit
:derives: REQ_RATE_LIMIT_ROUTING

**Constraint.** Rate-limit state shall remain isolated per provider and key, apply the more conservative configured request interval, and reset transient failure state after success.

**Rationale.** Sharing limiter state across unrelated providers or keys would create false throttling, while retaining transient failure state after recovery would make routing progressively less accurate.

**Verification intent.** Verify limiter state directly across multiple provider/key identities, interval combinations, failure updates, and subsequent successful updates.
```
