# mutation-pin: REQ_ASYNC_PROVIDER_EXECUTION e1a047184fcbb294
# pinned-by: claude-opus-5-5
# written-by: claude-opus-5-5, the last resort, the verdict's own model with tools
from __future__ import annotations

import pytest

from llm_router import LLMRouter, Model, Provider, RouterProfile
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
    patched_openai_sdk,
)

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_ASYNC_PROVIDER_EXECUTION[revision==1]")
@pytest.mark.asyncio
async def test_async_prepare_failure_is_traced_before_successful_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missing_env = "OPENROUTER_API_KEY_7"
    ready_env = "OPENROUTER_API_KEY_2"
    value = "local-route-value"
    monkeypatch.delenv(missing_env, raising=False)
    monkeypatch.setenv(ready_env, value)

    router = LLMRouter(
        [
            RouterProfile(
                model=Model.DEEPSEEK_V3,
                provider=Provider.OPENROUTER,
                key_id=7,
            ),
            RouterProfile(
                model=Model.DEEPSEEK_V3,
                provider=Provider.OPENROUTER,
                key_id=2,
            ),
        ],
        round_robin_start=False,
        shuffle_fallbacks=False,
        temperature=0.0,
    )

    with (
        ScriptedHTTPServer(
            port=0,
            routes={
                ("POST", openai_chat_path()): [
                    ScriptedResponse(
                        status_code=200,
                        headers={"Content-Type": "application/json"},
                        body=openai_success_response(text="fallback ok"),
                    )
                ]
            },
        ) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
    ):
        response = await router.aquery("Reply with the marker only.")

    assert response.output_text == "fallback ok"
    trace = response.routing_trace
    assert len(trace) == 2
    first = next(iter(trace))
    final = next(iter(reversed(trace)))
    assert first.key_id == 7
    assert first.error_type == "ApiKeyNotFoundError"
    assert first.error_message is not None
    assert missing_env in first.error_message
    assert final.key_id == 2
    assert final.error_type is None
    assert final.error_message is None
    assert first.route_index < final.route_index
