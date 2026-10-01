# mutation-pin: REQ_ASYNC_PROVIDER_EXECUTION 8a48c40fdfe50bce
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import pytest

from llm_router import LLMRouter, Model, Provider, RouterProfile
from tests.llm_router.support.fault_server import (
    ScriptedHTTPServer,
    ScriptedResponse,
)
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_error_response,
    openai_success_response,
    patched_openai_sdk,
)

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.asyncio
@pytest.mark.verifies("REQ_ASYNC_PROVIDER_EXECUTION[revision==1]")
async def test_async_fallback_trace_records_call_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for route_id in (1, 2):
        monkeypatch.setenv(f"OPENROUTER_API_KEY_{route_id}", f"auth-{route_id}")
    router = LLMRouter(
        [
            RouterProfile(
                provider=Provider.OPENROUTER,
                model=Model.DEEPSEEK_V3,
                key_id=route_id,
            )
            for route_id in (1, 2)
        ],
        round_robin_start=False,
        shuffle_fallbacks=False,
    )
    failure = ScriptedResponse(
        status_code=400,
        headers={"Content-Type": "application/json"},
        body=openai_error_response(status_code=400, message="route-one-failed"),
    )
    success = ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=openai_success_response(text="second-route-ok"),
    )
    with (
        ScriptedHTTPServer(
            port=0,
            routes={("POST", openai_chat_path()): [failure, success]},
        ) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
    ):
        response = await router.aquery("hello")

    assert response.output_text == "second-route-ok"
    first = response.routing_trace[0]
    assert first.error_type is not None
    assert first.error_message
    assert response.routing_trace[-1].error_type is None
