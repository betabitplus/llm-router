# mutation-pin: TREQ_GEMINI_WEBAPI_ADAPTER_BOUNDARY f0eefabee6b35a0a
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import pytest

from llm_router._api.types import Model, Provider, ProviderLimits
from llm_router._internal.config import (
    BehaviorDefaults,
    LLMRouterConfig,
    ProviderCatalog,
    RetryPolicy,
    RouterPolicyDefaults,
)
from llm_router._internal.providers.gemini_webapi import GeminiWebAPIAdapter
from llm_router._internal.providers.registry import get_adapter

pytestmark = pytest.mark.verification_kind("unit")

LIMITS = ProviderLimits(
    rps=100.0,
    rpm=6000.0,
    cooldown_seconds=1.0,
    cooldown_after_failures=3,
)


def _config() -> LLMRouterConfig:
    retry = RetryPolicy(min_wait_seconds=0.0, max_wait_seconds=0.0, max_attempts=3)
    policy = RouterPolicyDefaults(
        max_attempts=None,
        attempt_timeout_seconds=None,
        wait_for_cooldown_if_all_blocked=False,
        round_robin_start=False,
        shuffle_fallbacks=False,
        min_routes_for_fallback_shuffle=2,
        default_limits=LIMITS,
    )
    defaults = BehaviorDefaults(
        retry_policy=retry,
        policy=policy,
        default_max_tool_rounds=1,
        structured_output_max_attempts=1,
        provider_limits=LIMITS,
    )
    return LLMRouterConfig(
        default_provider=Provider.GROQ,
        default_model=Model.LLAMA_8B,
        default_key_id=1,
        defaults=defaults,
        catalog=ProviderCatalog(),
    )


@pytest.mark.verifies("TREQ_GEMINI_WEBAPI_ADAPTER_BOUNDARY[revision==1]")
def test_gemini_webapi_provider_resolves_to_webapi_adapter() -> None:
    adapter = get_adapter(provider=Provider.GEMINI_WEBAPI, config=_config())

    assert isinstance(adapter, GeminiWebAPIAdapter)
