# Request Lifecycle

## Construction

The public `LLMRouter` facade forwards route intent, optional session state,
generation defaults, policy defaults, and provider kwargs to `RouterRuntime`.
The runtime captures the current config snapshot, expands the route plan, stores
router defaults separately from provider kwargs, creates per-router key and
limiter state, and installs the default provider-route executor.

## Request Execution

For `query()` and `aquery()`, the runtime:

01. creates a request id,
02. resolves settings for the first route to decide attempt order,
03. resolves per-route effective settings as each candidate is considered,
04. resolves the provider key without logging the key value,
05. checks the provider/key limiter bucket,
06. builds session-aware provider-neutral messages,
07. executes the selected route through the provider-route executor,
08. records limiter success or failure,
09. attaches routing trace entries to the response,
10. remembers the session turn only after a successful normalized response.

The executor converts the resolved route into a `ProviderRequest`, calls the
selected adapter through same-route retry, runs local tool rounds, runs
structured-output repair when a schema is active, and returns a public
`LLMRouterResponse`. `ProviderRequest` carries the stable route index so
provider, retry, schema, and tool logs can be correlated with the public routing
trace without exposing request payloads.

Text-only role-less sequences keep separate provider messages, so replayed
chat-completion requests and live providers see the same turn shape. Mixed
content sequences remain one multimodal user message to preserve media ordering.

## Fallback And Waiting

Preparation failures such as an unknown provider or missing API key become
failed route traces and allow fallback routes to run.

Limiter-blocked routes are deferred instead of slept immediately. This lets the
router continue to an unblocked fallback route. Only when all considered routes
are blocked does the wait policy decide between fast failure and sleeping for
the shortest blocked route.

## Sync And Async Parity

The sync and async paths share the same route order, key resolution, limiter,
trace, fallback, session, and timeout decisions. The only difference is the
executor call and sleep primitive used by the final route attempt.

Both paths build public responses before session persistence. Failed requests do
not append turns to the session, so persisted history never records a misleading
assistant reply for a route that failed.
