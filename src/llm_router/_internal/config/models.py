"""Immutable runtime configuration models.

Why:
    Keeps config snapshots explicit and dataclass-compatible while later
    phases add validation and route-expansion behavior around them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING

from llm_router._api.types import Model, Provider

if TYPE_CHECKING:
    from collections.abc import Mapping

    from llm_router._api.types import ProviderLimits


def _freeze_mapping[K, V](mapping: Mapping[K, V]) -> Mapping[K, V]:
    """Return an immutable copy of a mapping."""
    return MappingProxyType(dict(mapping))


def _freeze_model_registry(
    models: Mapping[Model, Mapping[Provider, str]],
) -> Mapping[Model, Mapping[Provider, str]]:
    """Return an immutable copy of the nested model registry."""
    return MappingProxyType(
        {
            model: MappingProxyType(dict(provider_models))
            for model, provider_models in models.items()
        }
    )


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Provider-level retry defaults for one config snapshot."""

    min_wait_seconds: float
    max_wait_seconds: float
    max_attempts: int


@dataclass(frozen=True, slots=True)
class RouterPolicyDefaults:
    """Route fallback, timeout, and limiter defaults."""

    max_attempts: int | None
    attempt_timeout_seconds: float | None
    wait_for_cooldown_if_all_blocked: bool
    round_robin_start: bool
    shuffle_fallbacks: bool
    min_routes_for_fallback_shuffle: int
    default_limits: ProviderLimits
    limits_by_provider: Mapping[Provider, ProviderLimits] = field(
        default_factory=dict,
    )

    def __post_init__(self) -> None:
        """Freeze mutable mapping input after dataclass construction."""
        object.__setattr__(
            self,
            "limits_by_provider",
            _freeze_mapping(self.limits_by_provider),
        )


@dataclass(frozen=True, slots=True)
class BehaviorDefaults:
    """Installed defaults snapshot shared by config and routing."""

    retry_policy: RetryPolicy
    policy: RouterPolicyDefaults
    default_max_tool_rounds: int
    structured_output_max_attempts: int
    provider_limits: ProviderLimits
    limits_by_provider: Mapping[Provider, ProviderLimits] = field(
        default_factory=dict,
    )

    def __post_init__(self) -> None:
        """Freeze mutable mapping input after dataclass construction."""
        object.__setattr__(
            self,
            "limits_by_provider",
            _freeze_mapping(self.limits_by_provider),
        )


@dataclass(frozen=True, slots=True)
class ProviderSpec:
    """Configured provider identity and credential lookup metadata."""

    provider: Provider
    api_key_env_var: str | None = None
    api_key_env_vars: Mapping[int, str] = field(default_factory=dict)
    base_url: str | None = None

    def __post_init__(self) -> None:
        """Freeze mutable mapping input after dataclass construction."""
        object.__setattr__(
            self,
            "api_key_env_vars",
            _freeze_mapping(self.api_key_env_vars),
        )


@dataclass(frozen=True, slots=True)
class ProviderCatalog:
    """Installed provider declarations and model registry."""

    providers: Mapping[Provider, ProviderSpec] = field(default_factory=dict)
    provider_base_urls: Mapping[Provider, str] = field(default_factory=dict)
    models: Mapping[Model, Mapping[Provider, str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Freeze mutable mapping input after dataclass construction."""
        object.__setattr__(self, "providers", _freeze_mapping(self.providers))
        object.__setattr__(
            self,
            "provider_base_urls",
            _freeze_mapping(self.provider_base_urls),
        )
        object.__setattr__(self, "models", _freeze_model_registry(self.models))


@dataclass(frozen=True, slots=True)
class LLMRouterConfig:
    """Immutable runtime config snapshot captured by router instances."""

    default_provider: Provider
    default_model: Model
    default_key_id: int
    defaults: BehaviorDefaults
    catalog: ProviderCatalog

    @property
    def retry_policy(self) -> RetryPolicy:
        """Return the installed provider retry policy."""
        return self.defaults.retry_policy

    @property
    def policy(self) -> RouterPolicyDefaults:
        """Return the installed router policy defaults."""
        return self.defaults.policy

    @property
    def default_max_tool_rounds(self) -> int:
        """Return the installed default tool-round limit."""
        return self.defaults.default_max_tool_rounds

    @property
    def structured_output_max_attempts(self) -> int:
        """Return the installed structured-output repair attempt limit."""
        return self.defaults.structured_output_max_attempts

    @property
    def provider_limits(self) -> ProviderLimits:
        """Return the installed default provider limiter settings."""
        return self.defaults.provider_limits

    @property
    def limits_by_provider(self) -> Mapping[Provider, ProviderLimits]:
        """Return installed provider-specific limiter overrides."""
        return self.defaults.limits_by_provider

    @property
    def provider_base_urls(self) -> Mapping[Provider, str]:
        """Return installed provider base URL overrides."""
        return self.catalog.provider_base_urls

    @property
    def models(self) -> Mapping[Model, Mapping[Provider, str]]:
        """Return the installed public-model registry."""
        return self.catalog.models
