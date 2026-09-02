# Separate provider retry from route fallback

```{adr} Separate provider retry from route fallback
:id: ADR_0002
:status: accepted
:decision_date: 2026-08-31
:affects: REQ_PROVIDER_RETRY, REQ_SYNC_ROUTE_FALLBACK, REQ_ROUTE_ATTEMPT_LIMIT, IMPL_PROVIDER_RETRY, IMPL_PROVIDER_RETRY_CLASSIFICATION, IMPL_SYNC_ROUTE_FALLBACK, IMPL_ROUTE_ATTEMPT_LIMIT

**Context.** A failed request can represent two different recovery choices: retry
the same provider route because its failure is temporary, or abandon that route
and try another eligible route. Treating both as one undifferentiated attempt loop
would blur retry policy, route-attempt limits, fallback traces, and rate-limit
state.

**Decision.** Keep same-route provider retry inside `ProviderRouteExecutor` and
keep cross-route fallback in `LLMRouter`. The executor retries the same resolved
provider request only when the normalized provider failure is classified as
retryable. Once that executor attempt succeeds or raises, the router records the
route outcome and decides whether to continue to another eligible route. Provider
retry limits and route-attempt limits therefore remain separate controls.

**Consequences.** Temporary failures can receive bounded same-route recovery
without consuming additional route identities, while exhausted or permanent
failures can still participate in router fallback. Routing traces describe route
attempts; retry-specific diagnostics remain attached to the inner provider retry
loop. The two recovery layers must remain coordinated so timeout, limiter, and
error translation behavior does not accidentally bypass either budget.

**Alternatives considered.** Flatten provider retries and route fallback into one
attempt loop; immediately move to another route after the first temporary
failure; or hide all retry behavior inside each concrete provider adapter. These
alternatives either collapse two independently configurable recovery policies or
make retry behavior inconsistent across providers and harder for shared runtime
orchestration to observe.
```
