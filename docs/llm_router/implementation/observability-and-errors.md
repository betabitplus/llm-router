# Observability And Errors

## Scope

Runtime logs and public errors describe routing, provider execution, retry, and
session outcomes without exposing API keys or full provider payloads.

## Event Vocabulary

The private runtime uses stable `event_type` values:

| Area             | Events                                                                                                                                                                                                                                                |
| ---------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Config           | `llm_router.config.runtime.resolved`, `llm_router.config.runtime.installed`, `llm_router.config.adapter_caches.cleared`                                                                                                                               |
| Router lifecycle | `llm_router.router.request.started`, `llm_router.router.request.completed`, `llm_router.router.request.failed`                                                                                                                                        |
| Route planning   | `llm_router.routing.routes.expanded`, `llm_router.routing.route.selected`, `llm_router.routing.route.skipped`                                                                                                                                         |
| Attempts         | `llm_router.routing.attempt.started`, `llm_router.routing.attempt.succeeded`, `llm_router.routing.attempt.failed`, `llm_router.routing.attempt.timeout`                                                                                               |
| Limits           | `llm_router.routing.limit.waiting`, `llm_router.routing.limit.blocked`, `llm_router.routing.cooldown.opened`, `llm_router.routing.cooldown.cleared`                                                                                                   |
| Provider calls   | `llm_router.provider.request.started`, `llm_router.provider.request.completed`, `llm_router.provider.request.failed`, `llm_router.provider.upload.started`, `llm_router.provider.upload.completed`, `llm_router.provider.runtime.preflight.completed` |
| Retries          | `llm_router.provider.retry.scheduled`, `llm_router.provider.retry.exhausted`                                                                                                                                                                          |
| Schema repair    | `llm_router.capability.schema.validation.failed`, `llm_router.capability.schema.repair.started`, `llm_router.capability.schema.repair.succeeded`, `llm_router.capability.schema.repair.exhausted`                                                     |
| Tools            | `llm_router.capability.tool.called`, `llm_router.capability.tool.completed`, `llm_router.capability.tool.failed`, `llm_router.capability.tool.round_limit_reached`                                                                                    |
| Sessions         | `llm_router.session.turn.remembered`, `llm_router.session.saved`, `llm_router.session.loaded`, `llm_router.session.forked`, `llm_router.session.cleared`                                                                                              |

The discovery plan also names `profile_index` as a possible common field. The
current runtime flattens profiles into `ExpandedRoute` values during route
planning, so `route_index` is the emitted correlation field.

## Safe Field Rules

Common fields are flat primitives when available:

- `event_type`
- `request_id`
- `provider`
- `model`
- `route_index`
- `key_id`
- `attempt_number`
- `tool_round`
- `tool_name`
- `schema_name`
- `wait_seconds`
- `timeout_seconds`
- `duration_ms`
- `error_type`
- `error_message`
- `result_status`

Logs may include provider names, model names, route indexes, key ids, wait
durations, status codes, retry reasons, bounded error previews, optional cookie
presence booleans, route counts, and counts of persisted session turns.

Logs must not include API key values, cookie values, raw prompts, raw assistant
answers, raw file bytes, base64 media, provider-native request bodies, raw
provider response bodies, tool arguments, tool results, or full exception reprs.

## Retry Logging

Same-provider retries are owned by the provider-route executor. Provider
adapters classify failures into retryable or non-retryable `ProviderFailure`
records, then raise public `ProviderError` values with those failures as the
cause.

Tenacity retry hooks emit stable provider retry events:

- `llm_router.provider.retry.scheduled` for a retryable failure before the next
  same-route attempt.
- `llm_router.provider.retry.exhausted` when the final same-route attempt still
  fails.

Retry context includes request id, provider, model, key id, attempt number, and
route index when the request came from a route attempt. Error values use
bounded previews. Same-route retry attempts are not route fallback attempts;
route fallback traces stay at the router layer.

## Route And Capability Logs

`RouterRuntime` emits route expansion, request lifecycle, route selection,
blocked-route skip, wait-policy, attempt success, attempt failure, and timeout
events. These logs are diagnostics only; public routing traces remain the
deterministic response data.

`ProviderRouteExecutor` emits schema validation, repair, tool call, tool
completion, tool failure, and tool round-limit events. These events carry
request/provider/model/route/key context and capability names, but not schema
bodies, invalid provider output, tool arguments, or tool results.

Session logs record turn counts, file paths, and persistence actions. They do
not log session system text, user prompts, assistant replies, or persisted
message bodies.

## Error Translation

Adapters translate transport, SDK, HTTP status, provider API, response-format,
and runtime preflight failures into public `ProviderError` values. Private or
third-party exceptions are wrapped at adapter or executor boundaries before they
leave the runtime.

Retry classification is conservative:

- HTTP `408`, `409`, `429`, and server statuses are retryable.
- caller/auth statuses such as `400`, `401`, `403`, `404`, and `422` are not.
- transport-style exception type names are tokenized before matching so
  unrelated words such as `overwrite` do not look like write-transport errors.
- Gemini WebAPI status text such as `Status: 500` is parsed when the SDK does
  not expose a numeric status attribute.

Local tool failures cross the public boundary as `ToolExecutionError`. Exhausted
structured-output repair crosses as `ProviderError` with a bounded validation
message.

## Public Output Boundary

Successful provider results are converted to `LLMRouterResponse` at the runtime
boundary. Response data is JSON-safe: Pydantic models, dataclasses, mappings,
sequences, usage values, and scalar values are normalized before crossing the
public boundary. Unknown objects become bounded preview mappings rather than raw
SDK objects.

Normalized mapping data still supports attribute-style access for existing
callers, while preserving ordinary dict-style indexing and equality.
