"""Runtime config validation helpers.

Why:
    Centralizes provider, model, base URL, and policy invariant checks before
    snapshots are installed.
"""

from __future__ import annotations

from llm_router._internal.config.defaults import _PROVIDERS_REQUIRING_BASE_URL
from llm_router._internal.contracts.errors import ConfigurationError
from llm_router._internal.config.models import LLMRouterConfig


def _require(*, condition: bool, message: str) -> None:
    """Raise a public config error when a config invariant fails."""
    if not condition:
        raise ConfigurationError(message)


def validate_config(config: LLMRouterConfig) -> None:
    """Validate one runtime config snapshot."""
    retry = config.retry_policy
    _require(
        condition=retry.min_wait_seconds > 0,
        message="retry min wait must be greater than 0.",
    )
    _require(
        condition=retry.max_wait_seconds >= retry.min_wait_seconds,
        message="retry max wait is invalid.",
    )
    _require(
        condition=retry.max_attempts >= 1,
        message="retry max attempts must be at least 1.",
    )

    policy = config.policy
    if policy.max_attempts is not None:
        _require(
            condition=policy.max_attempts >= 1,
            message="policy max attempts must be at least 1.",
        )
    if policy.attempt_timeout_seconds is not None:
        _require(
            condition=policy.attempt_timeout_seconds > 0,
            message="policy attempt timeout must be greater than 0.",
        )
    _require(
        condition=policy.min_routes_for_fallback_shuffle >= 1,
        message="minimum routes for fallback shuffle must be at least 1.",
    )

    _require(
        condition=config.default_max_tool_rounds >= 1,
        message="default max tool rounds must be at least 1.",
    )
    _require(
        condition=config.structured_output_max_attempts >= 1,
        message="structured output max attempts must be at least 1.",
    )
    _require(
        condition=config.default_provider in config.catalog.providers,
        message="default provider must be present in the provider catalog.",
    )
    _require(
        condition=config.default_model in config.models,
        message="default model must be present in the model registry.",
    )
    _require(
        condition=config.default_provider in config.models[config.default_model],
        message="default model must have a mapping for the default provider.",
    )

    for provider, spec in config.catalog.providers.items():
        _require(
            condition=provider == spec.provider,
            message="provider spec key must match provider.",
        )

    for provider in _PROVIDERS_REQUIRING_BASE_URL:
        _require(
            condition=provider in config.provider_base_urls,
            message=f"provider '{provider.value}' requires a base URL.",
        )

    for model, provider_models in config.models.items():
        _require(
            condition=bool(provider_models),
            message=f"model '{model.value}' must map to a provider.",
        )
        for provider in provider_models:
            _require(
                condition=provider in config.catalog.providers,
                message=f"model '{model.value}' references an unknown provider.",
            )
