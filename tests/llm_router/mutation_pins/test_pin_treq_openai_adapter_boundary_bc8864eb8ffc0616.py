# mutation-pin: TREQ_OPENAI_ADAPTER_BOUNDARY bc8864eb8ffc0616
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import pytest

from llm_router._api.types import Model, Provider, ProviderLimits
from llm_router._internal.capabilities.content import normalize_content
from llm_router._internal.config import (
    BehaviorDefaults,
    LLMRouterConfig,
    ProviderCatalog,
    RetryPolicy,
    RouterPolicyDefaults,
)
from llm_router._internal.providers.base import ProviderCredential, ProviderRequest
from llm_router._internal.providers.openai_compatible import (
    OPENAI_COMPATIBLE_PROVIDERS,
    OpenAICompatibleAdapter,
)
from llm_router._internal.providers.registry import get_adapter
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)

pytestmark = pytest.mark.verification_kind("unit")

LIMITS = ProviderLimits(
    rps=100.0,
    rpm=6000.0,
    cooldown_seconds=1.0,
    cooldown_after_failures=3,
)


def _config(base_url: str) -> LLMRouterConfig:
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
    urls = dict.fromkeys(OPENAI_COMPATIBLE_PROVIDERS, base_url)
    return LLMRouterConfig(
        default_provider=Provider.OPENROUTER,
        default_model=Model.DEEPSEEK_V3,
        default_key_id=1,
        defaults=defaults,
        catalog=ProviderCatalog(provider_base_urls=urls),
    )


def _request(provider: Provider) -> ProviderRequest:
    return ProviderRequest(
        request_id="req-1",
        provider=provider,
        model=Model.DEEPSEEK_V3,
        provider_model="deepseek/test",
        credential=ProviderCredential(
            key_id=1,
            env_var="OPENROUTER_API_KEY_1",
            value="credential-value",
        ),
        messages=[normalize_content("hello")],
    )


@pytest.mark.verifies("TREQ_OPENAI_ADAPTER_BOUNDARY[revision==1]")
def test_openai_compatible_providers_resolve_and_complete_over_http() -> None:
    providers = sorted(
        (p for p in OPENAI_COMPATIBLE_PROVIDERS if p is not Provider.AISTUDIO),
        key=lambda item: item.value,
    )
    assert providers
    for provider in providers:
        with ScriptedHTTPServer(
            port=0,
            routes={
                ("POST", openai_chat_path()): [
                    ScriptedResponse(
                        status_code=200,
                        body=openai_success_response(text="pong"),
                    )
                ]
            },
        ) as server:
            config = _config(f"{server.base_url}/v1")
            adapter = get_adapter(provider=provider, config=config)
            assert isinstance(adapter, OpenAICompatibleAdapter), provider.name
            result = adapter.execute(_request(provider))
            assert result.output_text == "pong"
