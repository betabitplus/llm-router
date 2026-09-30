# mutation-pin: TREQ_AISTUDIO_ADAPTER_BOUNDARY cf6979d01bc5ba63
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
from llm_router._internal.providers.aistudio import AIStudioAdapter
from llm_router._internal.providers.base import ProviderCredential, ProviderRequest
from llm_router._internal.providers.registry import get_adapter
from tests.llm_router.support.fault_server import (
    ScriptedHTTPServer,
    ScriptedResponse,
)
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
    return LLMRouterConfig(
        default_provider=Provider.AISTUDIO,
        default_model=Model.GEMINI_FLASH,
        default_key_id=1,
        defaults=defaults,
        catalog=ProviderCatalog(provider_base_urls={Provider.AISTUDIO: base_url}),
    )


@pytest.mark.verifies("TREQ_AISTUDIO_ADAPTER_BOUNDARY[revision==1]")
def test_registry_builds_aistudio_adapter_using_shared_text_transport() -> None:
    path = openai_chat_path()
    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", path): [
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=openai_success_response(text="openai ok"),
                )
            ]
        },
    ) as server:
        config = _config(f"{server.base_url}/v1")
        adapter = get_adapter(provider=Provider.AISTUDIO, config=config)

        assert isinstance(adapter, AIStudioAdapter)
        request = ProviderRequest(
            request_id="req-1",
            provider=Provider.AISTUDIO,
            model=Model.GEMINI_FLASH,
            provider_model="gemini-3.6-flash",
            credential=ProviderCredential(
                key_id=1,
                env_var="AISTUDIO_API_KEY_1",
                value="value",
            ),
            messages=[normalize_content("hello")],
        )
        result = adapter.execute(request)

        assert result.output_text == "openai ok"
        assert len(server.recorded_requests("POST", path)) == 1
