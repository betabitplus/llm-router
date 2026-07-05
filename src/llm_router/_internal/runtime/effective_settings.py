"""Effective request setting resolution.

Why:
    Owns precedence between installed config, route defaults, router defaults,
    and explicit per-call overrides.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from llm_router._api.errors import ConfigurationError
from llm_router._api.types import KeyId, Provider, ProviderLimits
from llm_router._internal.config import LLMRouterConfig
from llm_router._internal.runtime.routes import RouteGenerationDefaults

GENERATION_FIELDS = frozenset(
    {
        "key_id",
        "temperature",
        "seed",
        "response_schema",
        "tools",
        "tool_choice",
        "max_tool_rounds",
    }
)
CALL_OVERRIDE_FIELDS = GENERATION_FIELDS - {"key_id"}
POLICY_FIELDS = frozenset(
    {
        "max_attempts",
        "attempt_timeout_seconds",
        "wait_for_cooldown_if_all_blocked",
        "round_robin_start",
        "shuffle_fallbacks",
        "default_limits",
        "limits_by_provider",
    }
)
KNOWN_SETTING_FIELDS = GENERATION_FIELDS | POLICY_FIELDS


@dataclass(frozen=True, slots=True)
class RouterDefaults:
    """Constructor-level defaults captured by one router instance."""

    values: Mapping[str, object] = field(default_factory=dict)
    kwargs: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Freeze mapping inputs after construction."""
        object.__setattr__(self, "values", MappingProxyType(dict(self.values)))
        object.__setattr__(self, "kwargs", MappingProxyType(dict(self.kwargs)))


@dataclass(frozen=True, slots=True)
class EffectiveSettings:
    """Resolved request settings for one route attempt."""

    key_id: KeyId
    temperature: float | None
    seed: int | None
    response_schema: object | None
    tools: Sequence[object] | None
    tool_choice: str | dict[str, Any] | None
    max_tool_rounds: int | None
    kwargs: Mapping[str, object]
    max_attempts: int | None
    attempt_timeout_seconds: float | None
    wait_for_cooldown_if_all_blocked: bool
    round_robin_start: bool
    shuffle_fallbacks: bool
    default_limits: ProviderLimits
    limits_by_provider: Mapping[Provider, ProviderLimits]

    def __post_init__(self) -> None:
        """Freeze mapping inputs after construction."""
        object.__setattr__(self, "kwargs", MappingProxyType(dict(self.kwargs)))
        object.__setattr__(
            self,
            "limits_by_provider",
            MappingProxyType(dict(self.limits_by_provider)),
        )
        if self.tools is not None:
            object.__setattr__(self, "tools", tuple(self.tools))


def split_router_defaults(values: Mapping[str, object]) -> RouterDefaults:
    """Split constructor kwargs into setting defaults and provider kwargs."""
    settings: dict[str, object] = {}
    provider_kwargs: dict[str, object] = {}
    for key, value in values.items():
        if key in KNOWN_SETTING_FIELDS:
            if value is not None:
                _validate_router_default(field_name=key, value=value)
                settings[key] = value
        elif key.startswith("_"):
            continue
        else:
            provider_kwargs[key] = value
    return RouterDefaults(values=settings, kwargs=provider_kwargs)


def resolve_effective_settings(
    *,
    config: LLMRouterConfig,
    route_defaults: RouteGenerationDefaults,
    route_policy_defaults: Mapping[str, object],
    router_defaults: RouterDefaults,
    call_overrides: Mapping[str, object],
) -> EffectiveSettings:
    """Resolve effective route settings with public precedence semantics."""
    values: dict[str, object] = {
        "key_id": route_defaults.key_id,
        "temperature": None,
        "seed": None,
        "response_schema": None,
        "tools": None,
        "tool_choice": None,
        "max_tool_rounds": config.default_max_tool_rounds,
        "max_attempts": config.policy.max_attempts,
        "attempt_timeout_seconds": config.policy.attempt_timeout_seconds,
        "wait_for_cooldown_if_all_blocked": (
            config.policy.wait_for_cooldown_if_all_blocked
        ),
        "round_robin_start": config.policy.round_robin_start,
        "shuffle_fallbacks": config.policy.shuffle_fallbacks,
        "default_limits": config.policy.default_limits,
        "limits_by_provider": config.policy.limits_by_provider,
    }
    kwargs: dict[str, object] = dict(route_defaults.kwargs)

    _apply_route_generation_defaults(values, route_defaults)
    _apply_non_null(values, route_policy_defaults)
    _apply_non_null(values, router_defaults.values)
    kwargs.update(router_defaults.kwargs)

    call_provider_kwargs = {
        key: value
        for key, value in call_overrides.items()
        if key not in CALL_OVERRIDE_FIELDS
    }
    _apply_call_overrides(values, call_overrides)
    kwargs.update(call_provider_kwargs)

    return EffectiveSettings(
        key_id=values["key_id"],
        temperature=values["temperature"],
        seed=values["seed"],
        response_schema=values["response_schema"],
        tools=values["tools"],
        tool_choice=values["tool_choice"],
        max_tool_rounds=values["max_tool_rounds"],
        kwargs=kwargs,
        max_attempts=values["max_attempts"],
        attempt_timeout_seconds=values["attempt_timeout_seconds"],
        wait_for_cooldown_if_all_blocked=values["wait_for_cooldown_if_all_blocked"],
        round_robin_start=values["round_robin_start"],
        shuffle_fallbacks=values["shuffle_fallbacks"],
        default_limits=values["default_limits"],
        limits_by_provider=values["limits_by_provider"],
    )


def _apply_route_generation_defaults(
    values: dict[str, object],
    route_defaults: RouteGenerationDefaults,
) -> None:
    """Apply non-null route generation defaults."""
    for field_name in GENERATION_FIELDS:
        value = getattr(route_defaults, field_name)
        if value is not None:
            values[field_name] = value


def _apply_non_null(
    values: dict[str, object],
    overrides: Mapping[str, object],
) -> None:
    """Apply only non-null overrides for default layers."""
    for key, value in overrides.items():
        if key in values and value is not None:
            values[key] = value


def _apply_call_overrides(
    values: dict[str, object],
    call_overrides: Mapping[str, object],
) -> None:
    """Apply explicit call overrides, including explicit `None` clearing."""
    values.update(
        {
            key: value
            for key, value in call_overrides.items()
            if key in CALL_OVERRIDE_FIELDS
        }
    )


def _validate_router_default(*, field_name: str, value: object) -> None:
    """Validate constructor-owned setting defaults."""
    if field_name == "max_attempts" and isinstance(value, int) and value < 1:
        msg = "router policy max attempts must be at least 1."
        raise ConfigurationError(msg)
    if (
        field_name == "attempt_timeout_seconds"
        and isinstance(value, int | float)
        and value <= 0
    ):
        msg = "router policy attempt timeout must be greater than 0."
        raise ConfigurationError(msg)
