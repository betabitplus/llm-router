# Routing requirements

{doc}`← Intent map <index>` · {doc}`Whole-system map <maps>` · {doc}`Release health <../specification-health>`

Read this page as one continuous branch of the product idea. Start with the local
**Idea branch** for the big picture. Then inspect only the contracts you care about;
under each Requirement/Technical requirement, **Follow this contract to proof** reveals one downstream hop so
you can drill into implementation or executed verification without opening a global
catalogue.

```{goal} Preserve request progress across route failures
:id: GOAL_ROUTING_RELIABILITY
:collapse: true

Routing should continue predictably when another eligible route can satisfy a request after an earlier route fails or is temporarily unavailable.
```

## Idea branch

This is the whole local intent hierarchy. Use the graph to see the forest; use the
clickable next-level links below it to enter the branch you want.

::::{only} graphviz_available

```{needflow} Routing reliability idea branch
:engine: graphviz
:direction: down
:root_id: GOAL_ROUTING_RELIABILITY
:root_direction: incoming
:root_depth: 3
:filter: type in ["goal", "feature", "req", "treq"]
:link_types: derives
:alt: Routing reliability from goal through requirements and technical requirements
```

::::

::::{only} not graphviz_available
The graph renderer is unavailable in this build. The authoritative Goal, Capability,
Requirement, and Technical requirement cards below preserve the same hierarchy through their relationship
links.
::::

### Enter this branch

```{needlist}
:filter: "'GOAL_ROUTING_RELIABILITY' in derives"
```

## See this branch as executable behavior

When you want to verify the public behavior at this abstraction level before opening
individual test evidence, use the Living Specifications for this branch. They keep
Gherkin, current execution status, attachments, and the exact requirement provenance
together.

- {ref}`Routing executable behavior <living-specs-area-routing>`

```{feature} Route fallback
:id: FEAT_ROUTE_FALLBACK
:collapse: true
:derives: GOAL_ROUTING_RELIABILITY

The router can move between eligible routes while respecting timeout, attempt-count, and subsequent-start policies.
```

Contracts in this capability:

```{needlist}
:filter: "'FEAT_ROUTE_FALLBACK' in derives"
```

```{req} Synchronous failed-route fallback
:id: REQ_SYNC_ROUTE_FALLBACK
:collapse: true
:status: accepted
:revision: 1
:required_evidence: impl;bdd
:derives: FEAT_ROUTE_FALLBACK

**Statement.** During a synchronous request, when an attempted route fails before producing a successful response and another eligible route remains, the router shall continue with the next route. A successful result shall expose routing trace entries for both the failed attempt and the route that ultimately succeeded.

**Rationale.** A transient failure on one route should not turn into a user-visible request failure when another configured route can still satisfy the request, and the caller needs enough trace information to explain the fallback.
```

::::{dropdown} Follow this contract to proof

```{needlist}
:filter: "'REQ_SYNC_ROUTE_FALLBACK' in derives or 'REQ_SYNC_ROUTE_FALLBACK' in implements or 'REQ_SYNC_ROUTE_FALLBACK' in verifies"
```

::::

```{req} Route timeout fallback
:id: REQ_ROUTE_TIMEOUT_FALLBACK
:collapse: true
:status: accepted
:revision: 1
:required_evidence: impl;bdd
:derives: FEAT_ROUTE_FALLBACK

**Statement.** An attempt timeout shall stop waiting on the current route, continue to another eligible route when one remains, and surface a timeout error when no fallback remains.

**Rationale.** A slow or stalled provider must not consume the whole request indefinitely or prevent another eligible route from making progress.
```

::::{dropdown} Follow this contract to proof

```{needlist}
:filter: "'REQ_ROUTE_TIMEOUT_FALLBACK' in derives or 'REQ_ROUTE_TIMEOUT_FALLBACK' in implements or 'REQ_ROUTE_TIMEOUT_FALLBACK' in verifies"
```

::::

```{req} Route attempt limit
:id: REQ_ROUTE_ATTEMPT_LIMIT
:collapse: true
:status: accepted
:revision: 1
:required_evidence: impl;bdd;unit
:derives: FEAT_ROUTE_FALLBACK

**Statement.** A request shall never attempt more routes than the configured route-attempt limit.

**Rationale.** Fallback must remain bounded so that a failing request cannot fan out across an uncontrolled number of providers or keys.
```

::::{dropdown} Follow this contract to proof

```{needlist}
:filter: "'REQ_ROUTE_ATTEMPT_LIMIT' in derives or 'REQ_ROUTE_ATTEMPT_LIMIT' in implements or 'REQ_ROUTE_ATTEMPT_LIMIT' in verifies"
```

::::

```{req} Successful route becomes the next starting route
:id: REQ_ROUTE_STICKY_START
:collapse: true
:status: accepted
:revision: 1
:required_evidence: impl;bdd
:derives: FEAT_ROUTE_FALLBACK

**Statement.** After fallback succeeds, the next request through the same router shall begin from the route that most recently succeeded.

**Rationale.** Reusing the most recently successful route avoids repeatedly paying for a known failing first attempt while preserving the configured route set.
```

::::{dropdown} Follow this contract to proof

```{needlist}
:filter: "'REQ_ROUTE_STICKY_START' in derives or 'REQ_ROUTE_STICKY_START' in implements or 'REQ_ROUTE_STICKY_START' in verifies"
```

::::

```{treq} Stable route ordering
:id: TREQ_ROUTE_ORDER
:collapse: true
:status: accepted
:revision: 1
:required_evidence: impl;unit
:derives: REQ_ROUTE_STICKY_START

**Statement.** Route ordering shall rotate or shuffle attempt order without losing the selected starting-route identity.

**Rationale.** Sticky-start behavior depends on stable route identity even when the candidate order is transformed internally.
```

::::{dropdown} Follow this contract to proof

```{needlist}
:filter: "'TREQ_ROUTE_ORDER' in derives or 'TREQ_ROUTE_ORDER' in implements or 'TREQ_ROUTE_ORDER' in verifies"
```

::::

```{feature} Rate-limit-aware routing
:id: FEAT_RATE_LIMIT_ROUTING
:collapse: true
:derives: GOAL_ROUTING_RELIABILITY

Routing accounts for per-provider and per-key availability before choosing or waiting for an attempt.
```

Contracts in this capability:

```{needlist}
:filter: "'FEAT_RATE_LIMIT_ROUTING' in derives"
```

```{req} Rate-limit-aware route and key selection
:id: REQ_RATE_LIMIT_ROUTING
:collapse: true
:status: accepted
:revision: 1
:required_evidence: impl;bdd
:derives: FEAT_RATE_LIMIT_ROUTING

**Statement.** Blocked routes shall be skipped when another route is available. When all routes are blocked, the router shall fail immediately or wait according to configured policy. Available credentials shall rotate before reuse requires waiting.

**Rationale.** Rate-limit state should guide routing decisions rather than turning an otherwise serviceable request into unnecessary delay or failure.
```

::::{dropdown} Follow this contract to proof

```{needlist}
:filter: "'REQ_RATE_LIMIT_ROUTING' in derives or 'REQ_RATE_LIMIT_ROUTING' in implements or 'REQ_RATE_LIMIT_ROUTING' in verifies"
```

::::

```{treq} Isolated limiter state
:id: TREQ_RATE_LIMIT_STATE
:collapse: true
:status: accepted
:revision: 1
:required_evidence: impl;unit
:derives: REQ_RATE_LIMIT_ROUTING

**Statement.** Rate-limit state shall remain isolated per provider and key, apply the more conservative configured request interval, and reset transient failure state after success.

**Rationale.** Sharing limiter state across unrelated providers or keys would create false throttling, while retaining transient failure state after recovery would make routing progressively less accurate.
```

::::{dropdown} Follow this contract to proof

```{needlist}
:filter: "'TREQ_RATE_LIMIT_STATE' in derives or 'TREQ_RATE_LIMIT_STATE' in implements or 'TREQ_RATE_LIMIT_STATE' in verifies"
```

::::

```{treq} Failure threshold opens a provider-key cooldown
:id: TREQ_RATE_LIMIT_COOLDOWN_POLICY
:collapse: true
:status: accepted
:revision: 1
:required_evidence: impl;unit
:derives: REQ_RATE_LIMIT_ROUTING

**Statement.** For each provider/key limiter bucket, when configured consecutive failures reach
`cooldown_after_failures`, the bucket shall remain unavailable for the configured
`cooldown_seconds` interval.

**Rationale.** Failure-based cooldown is part of the public limiter policy. If the threshold or
duration is ignored, repeated failures can continue to consume a route that the configured policy
declares temporarily unavailable.
```

::::{dropdown} Follow this contract to proof

```{needlist}
:filter: "'TREQ_RATE_LIMIT_COOLDOWN_POLICY' in derives or 'TREQ_RATE_LIMIT_COOLDOWN_POLICY' in implements or 'TREQ_RATE_LIMIT_COOLDOWN_POLICY' in verifies"
```

::::

```{treq} Availability-aware route and key selection
:id: TREQ_RATE_LIMIT_AVAILABILITY_SELECTION
:collapse: true
:status: accepted
:revision: 1
:required_evidence: impl;bdd
:derives: REQ_RATE_LIMIT_ROUTING

**Statement.** Automatic key selection shall choose an unblocked credential before a blocked
credential. When every eligible route/key candidate is blocked and waiting is enabled, the router
shall select the candidate with the shortest remaining wait.

**Rationale.** Rotation is only useful when it consumes available capacity. Waiting on a blocked key
while another credential is usable, or waiting longer than the earliest available candidate, adds
avoidable latency and contradicts the all-blocked waiting policy.
```

::::{dropdown} Follow this contract to proof

```{needlist}
:filter: "'TREQ_RATE_LIMIT_AVAILABILITY_SELECTION' in derives or 'TREQ_RATE_LIMIT_AVAILABILITY_SELECTION' in implements or 'TREQ_RATE_LIMIT_AVAILABILITY_SELECTION' in verifies"
```

::::

## Architecture decisions

The following accepted decision records explain routing boundaries that shape
these requirements without becoming additional product obligations.

```{needlist}
:filter: type == "adr" and "REQ_SYNC_ROUTE_FALLBACK" in affects
```

## Continue nearby

Do not jump back to an artifact catalogue when this branch raises a neighboring
question. These are the closest semantic continuations:

- {doc}`Configuration predictability <configuration>` — how route/request policy becomes effective.
- {doc}`Resilient execution <resilience>` — same-route retry and bounded recovery.
- {doc}`Provider portability <providers>` — what each provider boundary must preserve.

To zoom all the way out, return to the {doc}`Intent map <index>`. To investigate a release
blocker instead, open {doc}`Specification health <../specification-health>`.
