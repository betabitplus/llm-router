"""Built-in config assembly.

Why:
    Converts public default declarations into immutable private config
    snapshots before runtime work begins.
"""

from __future__ import annotations

from py_lib_runtime import get_logger

from llm_router._api import defaults as api_defaults
from llm_router._api.types import Provider
from llm_router._internal.config.models import (
    BehaviorDefaults,
    LLMRouterConfig,
    ProviderCatalog,
    ProviderSpec,
    RetryPolicy,
    RouterPolicyDefaults,
)
from llm_router._internal.config.validation import validate_config

logger = get_logger(__name__)


def _default_provider_specs() -> dict[Provider, ProviderSpec]:
    """Return provider specs copied from built-in provider declarations."""
    provider_base_urls = dict(api_defaults.DEFAULT_PROVIDER_BASE_URLS)
    return {
        provider: ProviderSpec(
            provider=provider,
            api_key_env_vars={api_defaults.DEFAULT_KEY_ID: _api_key_name(provider)},
            base_url=provider_base_urls.get(provider),
        )
        for provider in Provider
    }


def _api_key_name(provider: Provider) -> str:
    """Return the default environment variable name for a provider key."""
    return f"{provider.name}_API_KEY_{api_defaults.DEFAULT_KEY_ID}"


def build_default_config() -> LLMRouterConfig:
    """Assemble and validate the built-in runtime config snapshot."""
    retry_policy = RetryPolicy(
        min_wait_seconds=api_defaults.DEFAULT_RETRY_MIN_WAIT_SECONDS,
        max_wait_seconds=api_defaults.DEFAULT_RETRY_MAX_WAIT_SECONDS,
        max_attempts=api_defaults.DEFAULT_RETRY_MAX_ATTEMPTS,
    )
    policy = RouterPolicyDefaults(
        max_attempts=api_defaults.DEFAULT_POLICY_MAX_ATTEMPTS,
        attempt_timeout_seconds=api_defaults.DEFAULT_POLICY_ATTEMPT_TIMEOUT_SECONDS,
        wait_for_cooldown_if_all_blocked=(
            api_defaults.DEFAULT_POLICY_WAIT_FOR_COOLDOWN_IF_ALL_BLOCKED
        ),
        round_robin_start=api_defaults.DEFAULT_POLICY_ROUND_ROBIN_START,
        shuffle_fallbacks=api_defaults.DEFAULT_POLICY_SHUFFLE_FALLBACKS,
        min_routes_for_fallback_shuffle=(
            api_defaults.DEFAULT_POLICY_MIN_ROUTES_FOR_FALLBACK_SHUFFLE
        ),
        default_limits=api_defaults.DEFAULT_PROVIDER_LIMITS,
        limits_by_provider=dict(api_defaults.DEFAULT_LIMITS_BY_PROVIDER),
    )
    defaults = BehaviorDefaults(
        retry_policy=retry_policy,
        policy=policy,
        default_max_tool_rounds=api_defaults.DEFAULT_MAX_TOOL_ROUNDS,
        structured_output_max_attempts=(
            api_defaults.DEFAULT_STRUCTURED_OUTPUT_MAX_ATTEMPTS
        ),
        provider_limits=api_defaults.DEFAULT_PROVIDER_LIMITS,
        limits_by_provider=dict(api_defaults.DEFAULT_LIMITS_BY_PROVIDER),
    )
    catalog = ProviderCatalog(
        providers=_default_provider_specs(),
        provider_base_urls=dict(api_defaults.DEFAULT_PROVIDER_BASE_URLS),
        models={
            model: dict(provider_models)
            for model, provider_models in api_defaults.DEFAULT_MODEL_REGISTRY.items()
        },
    )
    config = LLMRouterConfig(
        default_provider=api_defaults.DEFAULT_PROVIDER,
        default_model=api_defaults.DEFAULT_MODEL,
        default_key_id=api_defaults.DEFAULT_KEY_ID,
        defaults=defaults,
        catalog=catalog,
    )
    validate_config(config)
    logger.info(
        "Runtime config resolved",
        event_type="llm_router.config.runtime.resolved",
        default_provider=config.default_provider.value,
        default_model=config.default_model.value,
        provider_count=len(config.catalog.providers),
        model_count=len(config.models),
    )
    return config
