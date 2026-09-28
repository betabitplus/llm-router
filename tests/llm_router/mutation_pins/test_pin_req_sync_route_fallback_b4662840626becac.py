# mutation-pin: REQ_SYNC_ROUTE_FALLBACK b4662840626becac
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router import LLMRouter, Model, Provider, RouterProfile
from tests.llm_router.support.fault_server import (
    ScriptedHTTPServer,
    ScriptedResponse,
)
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_SYNC_ROUTE_FALLBACK[revision==2]")
def test_sync_fallback_traces_preparation_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = "mock-credential-2"
    monkeypatch.delenv("OPENROUTER_API_KEY_1", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY_2", value)

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
    )

    chat_path = openai_chat_path()
    with (
        ScriptedHTTPServer(
            port=0,
            routes={
                ("POST", chat_path): [
                    ScriptedResponse(
                        status_code=200,
                        headers={"Content-Type": "application/json"},
                        body=openai_success_response(text="route-2-success"),
                    ),
                ]
            },
        ) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
    ):
        response = router.query("test-prompt")

    assert response.output_text == "route-2-success"
    assert [attempt.route_index for attempt in response.routing_trace] == [0, 1]
    assert response.routing_trace[0].error_type is not None
    assert response.routing_trace[1].error_type is None
