# mutation-pin: TREQ_GOOGLE_GENAI_ADAPTER_BOUNDARY 23c266a8950b1701
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
from llm_router._internal.providers.google_genai import GoogleGenAIAdapter
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
        default_provider=Provider.GOOGLE,
        default_model=Model.GEMINI_FLASH,
        default_key_id=1,
        defaults=defaults,
        catalog=ProviderCatalog(),
    )


@pytest.mark.verifies("TREQ_GOOGLE_GENAI_ADAPTER_BOUNDARY[revision==1]")
def test_google_provider_resolves_to_google_genai_adapter() -> None:
    adapter = get_adapter(provider=Provider.GOOGLE, config=_config())

    assert isinstance(adapter, GoogleGenAIAdapter)
