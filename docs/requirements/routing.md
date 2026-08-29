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
:revision: 1
:needs_artifacts: impl;bdd
:derives: FEAT_ROUTE_FALLBACK

During a synchronous request, when an attempted route fails before producing a successful response and another eligible route remains, the router must continue with the next route. A successful result must expose routing trace entries for both the failed attempt and the route that ultimately succeeded.
```

```{req} Route timeout fallback
:id: REQ_ROUTE_TIMEOUT_FALLBACK
:revision: 1
:needs_artifacts: impl;bdd
:derives: FEAT_ROUTE_FALLBACK

An attempt timeout must stop waiting on the current route, continue to another eligible route when one remains, and surface a timeout error when no fallback remains.
```

```{req} Route attempt limit
:id: REQ_ROUTE_ATTEMPT_LIMIT
:revision: 1
:needs_artifacts: impl;bdd
:derives: FEAT_ROUTE_FALLBACK

A request must never attempt more routes than the configured route-attempt limit.
```

```{req} Successful route becomes the next starting route
:id: REQ_ROUTE_STICKY_START
:revision: 1
:needs_artifacts: impl;bdd
:derives: FEAT_ROUTE_FALLBACK

After fallback succeeds, the next request through the same router must begin from the route that most recently succeeded.
```

```{treq} Stable route ordering
:id: TREQ_ROUTE_ORDER
:revision: 1
:needs_artifacts: impl;unit
:derives: REQ_ROUTE_STICKY_START

Route ordering must rotate or shuffle attempt order without losing the selected starting route identity.
```

```{feature} Rate-limit-aware routing
:id: FEAT_RATE_LIMIT_ROUTING
:derives: GOAL_ROUTING_RELIABILITY

Routing accounts for per-provider and per-key availability before choosing or waiting for an attempt.
```

```{req} Rate-limit-aware route and key selection
:id: REQ_RATE_LIMIT_ROUTING
:revision: 1
:needs_artifacts: impl;bdd
:derives: FEAT_RATE_LIMIT_ROUTING

Blocked routes must be skipped when another route is available; when all routes are blocked the router must either fail immediately or wait according to policy, and available keys must rotate before reuse requires waiting.
```

```{treq} Isolated limiter state
:id: TREQ_RATE_LIMIT_STATE
:revision: 1
:needs_artifacts: impl;unit
:derives: REQ_RATE_LIMIT_ROUTING

Rate-limit state must remain isolated per provider and key, apply the more conservative configured request interval, and reset transient failure state after success.
```
