# mutation-pin: REQ_ASYNC_PROVIDER_EXECUTION 4185d08c0ebf67fe
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
async def test_async_pacing_wait_under_one_second_defers_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_first = "OPENROUTER_API_KEY_1"
    env_second = "OPENROUTER_API_KEY_2"
    value = "mock-provider-auth-12345"
    monkeypatch.setenv(env_first, value)
    monkeypatch.setenv(env_second, value)
    path = openai_chat_path()
    limits = {
        Provider.OPENROUTER: ProviderLimits(
            rps=2.0,
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
                key_id=1,
            ),
            RouterProfile(
                provider=Provider.OPENROUTER,
                model=Model.DEEPSEEK_V3,
                key_id=2,
            ),
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
        first = await router.aquery("first prompt")
        second = await router.aquery("second prompt")

    assert [attempt.key_id for attempt in first.routing_trace] == [1]
    # Route 1 is paced for about half a second: it must be reported as
    # blocked and the ready route 2 must serve the request.
    assert [attempt.key_id for attempt in second.routing_trace] == [1, 2]
    assert [attempt.error_type for attempt in second.routing_trace] == [
        "RouteBlockedError",
        None,
    ]
    assert 0.0 < second.routing_trace[0].wait_seconds < 1.0
