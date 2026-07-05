"""Route expansion and ordering helpers.

Why:
    Keeps public route intent expansion separate from provider execution and
    limiter state.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from secrets import SystemRandom
from types import MappingProxyType
from typing import Any, Protocol

from llm_router._api.errors import ConfigurationError, ModelNotFoundError
from llm_router._api.types import KeyId, Model, Provider, RouterProfile
from llm_router._internal.config import LLMRouterConfig, get_config

_POLICY_FIELDS = (
    "max_attempts",
    "attempt_timeout_seconds",
    "wait_for_cooldown_if_all_blocked",
    "round_robin_start",
    "shuffle_fallbacks",
    "default_limits",
    "limits_by_provider",
)


@dataclass(frozen=True, slots=True)
class RouteGenerationDefaults:
    """Generation defaults attached to one expanded route."""

    key_id: KeyId
    temperature: float | None = None
    seed: int | None = None
    response_schema: object | None = None
    tools: tuple[object, ...] | None = None
    tool_choice: str | dict[str, Any] | None = None
    max_tool_rounds: int | None = None
    kwargs: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Copy mutable route defaults after dataclass construction."""
        object.__setattr__(self, "kwargs", MappingProxyType(dict(self.kwargs)))
        if self.tools is not None:
            object.__setattr__(self, "tools", tuple(self.tools))


@dataclass(frozen=True, slots=True)
class ExpandedRoute:
    """One concrete route candidate after model/provider expansion."""

    route_index: int
    model: Model
    provider: Provider | str
    provider_model: str
    defaults: RouteGenerationDefaults


class RouteShuffler(Protocol):
    """Minimal randomizer port used by route ordering."""

    def shuffle(self, routes: list[ExpandedRoute]) -> None:
        """Shuffle route fallbacks in place."""


@dataclass(frozen=True, slots=True)
class RouteOrderOptions:
    """Route-order policy for one request."""

    round_robin_start: bool
    shuffle_fallbacks: bool
    min_routes_for_fallback_shuffle: int
    request_index: int
    max_attempts: int | None
    shuffler: RouteShuffler | None = None


@dataclass(frozen=True, slots=True)
class RoutePlan:
    """Provider-neutral route plan for one router instance."""

    routes: tuple[ExpandedRoute, ...]
    policy_defaults: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Copy mutable policy defaults after dataclass construction."""
        object.__setattr__(self, "routes", tuple(self.routes))
        object.__setattr__(
            self,
            "policy_defaults",
            MappingProxyType(dict(self.policy_defaults)),
        )


def expand_route_plan(
    spec: Model | str | RouterProfile | Sequence[RouterProfile],
    *,
    config: LLMRouterConfig | None = None,
) -> RoutePlan:
    """Expand a public route spec into concrete route candidates."""
    active_config = get_config() if config is None else config
    profiles = _profiles_from_spec(spec, config=active_config)
    policy_defaults = _collect_policy_defaults(profiles)

    routes: list[ExpandedRoute] = []
    for profile in profiles:
        routes.extend(
            _expand_profile(profile, config=active_config, offset=len(routes))
        )

    if not routes:
        msg = "Route spec must define at least one route."
        raise ConfigurationError(msg)

    return RoutePlan(routes=tuple(routes), policy_defaults=policy_defaults)


def ordered_routes(
    plan: RoutePlan,
    *,
    options: RouteOrderOptions,
) -> tuple[ExpandedRoute, ...]:
    """Return route candidates in attempt order for one request."""
    routes = list(plan.routes)
    if not routes:
        return ()
    if options.round_robin_start:
        start = options.request_index % len(routes)
        routes = [*routes[start:], *routes[:start]]
    if (
        options.shuffle_fallbacks
        and len(routes) >= options.min_routes_for_fallback_shuffle
    ):
        shuffler = SystemRandom() if options.shuffler is None else options.shuffler
        fallbacks = routes[1:]
        shuffler.shuffle(fallbacks)
        routes = [routes[0], *fallbacks]
    if options.max_attempts is not None:
        routes = routes[: options.max_attempts]
    return tuple(routes)


def _profiles_from_spec(
    spec: object,
    *,
    config: LLMRouterConfig,
) -> tuple[RouterProfile, ...]:
    """Normalize public spec shapes into route profiles."""
    if isinstance(spec, RouterProfile):
        return (spec,)
    if isinstance(spec, Model | str):
        return (RouterProfile(model=_resolve_model(spec, config=config)),)
    if isinstance(spec, Sequence):
        profiles = tuple(spec)
        if not all(isinstance(profile, RouterProfile) for profile in profiles):
            msg = "Route sequences must contain only RouterProfile instances."
            raise TypeError(msg)
        return profiles

    msg = "Route spec must be a Model, RouterProfile, or sequence of RouterProfile."
    raise TypeError(msg)


def _expand_profile(
    profile: RouterProfile,
    *,
    config: LLMRouterConfig,
    offset: int,
) -> list[ExpandedRoute]:
    """Expand one profile into one or more concrete routes."""
    model = _resolve_model(profile.model, config=config)
    provider = _resolve_provider(profile.provider)
    defaults = _route_defaults(profile=profile, config=config)

    if provider is None:
        provider_models = _provider_models_for(model, config=config)
        ordered_providers = _ordered_providers(provider_models, config=config)
        return [
            ExpandedRoute(
                route_index=offset + index,
                model=model,
                provider=expanded_provider,
                provider_model=provider_models[expanded_provider],
                defaults=defaults,
            )
            for index, expanded_provider in enumerate(ordered_providers)
        ]

    if not isinstance(provider, Provider):
        return [
            ExpandedRoute(
                route_index=offset,
                model=model,
                provider=provider,
                provider_model=model.value,
                defaults=defaults,
            )
        ]

    provider_models = _provider_models_for(model, config=config)
    if provider not in provider_models:
        raise ModelNotFoundError(model, provider)
    return [
        ExpandedRoute(
            route_index=offset,
            model=model,
            provider=provider,
            provider_model=provider_models[provider],
            defaults=defaults,
        )
    ]


def _resolve_model(model: Model | str, *, config: LLMRouterConfig) -> Model:
    """Resolve public model input to the stable model enum."""
    if isinstance(model, Model):
        resolved = model
    else:
        try:
            resolved = Model(model)
        except ValueError as exc:
            msg = f"Unknown model: {model}"
            raise ConfigurationError(msg) from exc
    if resolved not in config.models:
        msg = f"Unknown model: {model}"
        raise ConfigurationError(msg)
    return resolved


def _resolve_provider(provider: Provider | str | None) -> Provider | str | None:
    """Resolve valid provider strings while preserving invalid fallback routes."""
    if provider is None or isinstance(provider, Provider):
        return provider
    try:
        return Provider(provider)
    except ValueError:
        return provider


def _provider_models_for(
    model: Model,
    *,
    config: LLMRouterConfig,
) -> dict[Provider, str]:
    """Return provider-native model mappings for one public model."""
    try:
        provider_models = config.models[model]
    except KeyError as exc:
        msg = f"Unknown model: {model.value}"
        raise ConfigurationError(msg) from exc
    return dict(provider_models)


def _ordered_providers(
    provider_models: dict[Provider, str],
    *,
    config: LLMRouterConfig,
) -> tuple[Provider, ...]:
    """Return deterministic providers with the default provider first when valid."""
    providers = list(provider_models)
    if config.default_provider in provider_models:
        providers.remove(config.default_provider)
        providers.insert(0, config.default_provider)
    return tuple(providers)


def _route_defaults(
    *,
    profile: RouterProfile,
    config: LLMRouterConfig,
) -> RouteGenerationDefaults:
    """Return generation defaults owned by one route profile."""
    key_id = config.default_key_id if profile.key_id is None else profile.key_id
    return RouteGenerationDefaults(
        key_id=key_id,
        temperature=profile.temperature,
        seed=profile.seed,
        response_schema=profile.response_schema,
        tools=None if profile.tools is None else tuple(profile.tools),
        tool_choice=profile.tool_choice,
        max_tool_rounds=profile.max_tool_rounds,
        kwargs=dict(profile.kwargs),
    )


def _collect_policy_defaults(
    profiles: tuple[RouterProfile, ...],
) -> Mapping[str, object]:
    """Collect non-conflicting router-wide policy defaults from profiles."""
    collected: dict[str, object] = {}
    for profile in profiles:
        for field_name in _POLICY_FIELDS:
            value = getattr(profile, field_name)
            if value is None:
                continue
            _validate_policy_default(field_name=field_name, value=value)
            candidate = _copy_policy_value(value)
            if field_name in collected and collected[field_name] != candidate:
                msg = f"Conflicting route policy default: {field_name}."
                raise ConfigurationError(msg)
            collected[field_name] = candidate
    return collected


def _copy_policy_value(value: object) -> object:
    """Copy mutable policy values before storing them in a route plan."""
    if isinstance(value, dict):
        return MappingProxyType(dict(value))
    return value


def _validate_policy_default(*, field_name: str, value: object) -> None:
    """Validate route-attached policy values before storing them."""
    if field_name == "max_attempts" and isinstance(value, int) and value < 1:
        msg = "route policy max attempts must be at least 1."
        raise ConfigurationError(msg)
    if (
        field_name == "attempt_timeout_seconds"
        and isinstance(value, int | float)
        and value <= 0
    ):
        msg = "route policy attempt timeout must be greater than 0."
        raise ConfigurationError(msg)
