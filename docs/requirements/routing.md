# Routing requirements

```{goal} Preserve request progress across route failures
:id: GOAL_ROUTING_RELIABILITY

Routing should continue when another eligible route can satisfy a request after an earlier route fails.
```

```{feature} Route fallback
:id: FEAT_ROUTE_FALLBACK
:derives: GOAL_ROUTING_RELIABILITY

The router can move from an unsuccessful route attempt to another eligible route while preserving observable attempt history.
```

```{req} Synchronous failed-route fallback
:id: REQ_SYNC_ROUTE_FALLBACK
:revision: 1
:needs_artifacts: impl;bdd
:derives: FEAT_ROUTE_FALLBACK

During a synchronous request, when an attempted route fails before producing a successful response and another eligible route remains, the router must continue with the next route. A successful result must expose routing trace entries for both the failed attempt and the route that ultimately succeeded.
```
