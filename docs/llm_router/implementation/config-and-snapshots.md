# Config And Snapshots

## Ownership

`src/llm_router/_internal/config` owns the private runtime config snapshot. The
public `_api.config` module re-exports the dataclasses and install/read helpers,
but mutable process state stays in `_internal.config.state`.

## Snapshot Shape

- `RetryPolicy`: provider retry wait and attempt defaults.
- `RouterPolicyDefaults`: route attempt, timeout, cooldown, ordering, and
  limiter defaults.
- `BehaviorDefaults`: the installed defaults bundle, including retry policy,
  route policy, tool limits, structured-output limits, and limiter defaults.
- `ProviderSpec`: provider identity and credential lookup metadata.
- `ProviderCatalog`: provider declarations, provider base URLs, and the public
  model registry.
- `LLMRouterConfig`: the immutable process-wide snapshot captured by future
  router instances.

## Default Assembly

`build_default_config()` copies declarations from `src/llm_router/_api/defaults.py`
into private dataclasses. Mutable mappings are copied when dataclasses are built
so installed config snapshots do not alias the defaults module or caller-owned
dicts.

## Validation

`validate_config()` checks retry limits, route policy limits, provider spec
keys, required provider base URLs, default provider/model availability, and
model-registry provider references before a snapshot is installed.

## Install Semantics

`install_config(config)` accepts only `LLMRouterConfig`, validates the snapshot,
then atomically replaces the process-wide installed config and clears provider
adapter caches.

## Route Expansion

`runtime.routes.expand_route_plan()` turns `Model`, `RouterProfile`, and
`Sequence[RouterProfile]` specs into provider-neutral route candidates without
constructing provider SDK clients.
