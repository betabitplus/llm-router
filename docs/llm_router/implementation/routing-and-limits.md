# Routing And Limits

## Scope

Phase 04 owns provider-neutral request policy. The runtime resolves effective
settings, orders routes, selects keys, applies limiter state, enforces per-route
attempt timeouts, and builds public routing traces before provider-specific SDK
payloads exist.

## Effective Settings

`RouterRuntime` captures the installed config snapshot during construction and
does not read global config during request execution. Each route attempt resolves
settings in this order:

```text
installed config < route defaults < router constructor defaults < explicit call overrides
```

Route and router default layers ignore `None`, which means inherit. Explicit
call `None` clears call-overridable generation fields such as
`response_schema`, `tools`, and `tool_choice`. `key_id` is a route/router
selection default; a hidden per-call `key_id` stays in provider kwargs rather
than changing credential selection.

## Route Order

Route specs are expanded into concrete `ExpandedRoute` values before execution.
Each route keeps its stable `route_index` for traces even when the attempt order
changes.

Router construction emits `llm_router.routing.routes.expanded` with the route
count. Per-request route decisions then use the same stable route index in
selection, attempt, blocked-route, retry, provider, schema, and tool events.

For each request, `ordered_routes()` applies:

1. optional round-robin start based on the router instance request index,
2. optional fallback shuffling after the start route when the route count meets
   the configured shuffle threshold,
3. optional `max_attempts` truncation as a route-attempt cap.

Provider retry counts remain separate from this route-attempt policy.

## Key Resolution

`KeyResolver` handles fixed numeric keys and `key_id="auto"`.

Fixed keys resolve through the configured provider key map first. If no custom
name exists, the generated name is `<PROVIDER_NAME>_API_KEY_<id>`, for example
`NVIDIA_API_KEY_2`.

Auto selection rotates across configured keys with present environment values
and discovered generated key names. Rotation is provider-local and stored on the
router runtime.

Missing keys raise the public `ApiKeyNotFoundError` with the expected env var
name, provider, and key id, except for local/browser-backed providers with
optional bearer tokens. `gemini_webapi` and `qwenchat` resolve a missing key to
an empty value so their local runtime paths can proceed without an auth header.
Key values are never copied into traces or logs.

## Limit Buckets

`LimiterState` stores one bucket per `(provider, key_id)`.

Successful attempts set the bucket's next available time from
`ProviderLimits.min_interval_seconds()`, which uses the conservative maximum of
the RPS and RPM intervals. Failed attempts increment the bucket failure count
and open a cooldown when `cooldown_after_failures` is reached.

Blocked routes are skipped while other candidates remain. If every available
candidate is blocked, the router either:

- raises `TimeoutError("All routes are blocked by provider/key limits.")` when
  waiting is disabled, or
- waits for the shortest blocked route to become available and then executes
  that same request when waiting is enabled.

## Timeouts And Traces

Sync and async paths enforce the same per-attempt timeout semantics. A timed-out
attempt records `TimeoutError` in the routing trace and the router moves to the
next candidate when one exists.

Public `RoutingAttempt` entries are provider-neutral. They include route index,
provider, model, key id, wait seconds, temperature, seed, max tool rounds, and
safe error type/message data. They do not include SDK payloads, API keys,
prompts, media bytes, or raw provider responses.

Successful responses receive all failed attempt traces, skipped blocked-route
traces when a fallback was used, any executor-provided traces, and the final
successful attempt trace.
