# mutation-pin: REQ_ASYNC_PROVIDER_EXECUTION b5451a90524408d8
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import pytest

from llm_router import LLMRouter, Model, Provider, ProviderLimits, RouterProfile
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
    patched_openai_sdk,
)

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_ASYNC_PROVIDER_EXECUTION[revision==1]")
@pytest.mark.asyncio
async def test_async_blocked_route_remembers_fallback_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = "mock-provider-auth-12345"
    for key_id in (1, 2, 3):
        monkeypatch.setenv(f"OPENROUTER_API_KEY_{key_id}", value)
    path = openai_chat_path()
    limits = {
        Provider.OPENROUTER: ProviderLimits(
            rps=0.5,
            rpm=1_000_000.0,
            cooldown_seconds=0.0,
            cooldown_after_failures=0,
        )
    }
    router = LLMRouter(
        [
            RouterProfile(
                provider=Provider.OPENROUTER,
                model=Model.DEEPSEEK_V3,
                key_id=key_id,
            )
            for key_id in (1, 2, 3)
        ],
        round_robin_start=False,
        shuffle_fallbacks=False,
        limits_by_provider=limits,
    )
    with (
        ScriptedHTTPServer(
            port=0,
            routes={
                ("POST", path): [
                    ScriptedResponse(
                        status_code=200,
                        headers={"Content-Type": "application/json"},
                        body=openai_success_response(text=marker),
                    )
                    for marker in ("A", "B", "C")
                ]
            },
        ) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
    ):
        await router.aquery("first prompt")
        second = await router.aquery("second prompt")
        third = await router.aquery("third prompt")

    assert [a.route_index for a in second.routing_trace] == [0, 1]
    assert [a.error_type for a in second.routing_trace] == ["RouteBlockedError", None]
    # The fallback route 1 is remembered, so the next request starts there.
    assert [a.route_index for a in third.routing_trace] == [1, 2]
