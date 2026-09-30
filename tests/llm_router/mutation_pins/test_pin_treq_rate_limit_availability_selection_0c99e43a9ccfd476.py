# mutation-pin: TREQ_RATE_LIMIT_AVAILABILITY_SELECTION 0c99e43a9ccfd476
# pinned-by: claude-opus-5-5
# written-by: claude-opus-5-5, the last resort, the verdict's own model with tools
from __future__ import annotations

import pytest

from llm_router import (
    LLMRouter,
    Model,
    Provider,
    ProviderError,
    ProviderLimits,
    RouterProfile,
)
from tests.llm_router.support.fault_server import (
    ScriptedHTTPServer,
    ScriptedResponse,
)
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_error_response,
    openai_success_response,
)
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

pytestmark = pytest.mark.verification_kind("unit")

CHAT_PATH = openai_chat_path()
# Key 2 is spaced by 0.25 s after a success; key 1 cools down for 2 s after a
# failure, so on the third request both keys are blocked and key 2 frees first.
LIMITS = ProviderLimits(
    rps=4.0,
    rpm=1_000_000.0,
    cooldown_seconds=2.0,
    cooldown_after_failures=1,
)


def _json_response(*, status_code: int, body: bytes) -> ScriptedResponse:
    return ScriptedResponse(
        status_code=status_code,
        headers={"Content-Type": "application/json"},
        body=body,
    )


@pytest.mark.verifies("TREQ_RATE_LIMIT_AVAILABILITY_SELECTION[revision==1]")
def test_all_blocked_auto_keys_wait_on_shortest_remaining_wait(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "openrouter-value-1")
    monkeypatch.setenv("OPENROUTER_API_KEY_2", "openrouter-value-2")
    router = LLMRouter(
        RouterProfile(
            provider=Provider.OPENROUTER,
            model=Model.DEEPSEEK_V3,
            key_id="auto",
        ),
        wait_for_cooldown_if_all_blocked=True,
        limits_by_provider={Provider.OPENROUTER: LIMITS},
    )
    responses = [
        _json_response(
            status_code=400,
            body=openai_error_response(status_code=400, message="cool key 1"),
        ),
        _json_response(
            status_code=200,
            body=openai_success_response(text="served by key 2"),
        ),
        _json_response(
            status_code=200,
            body=openai_success_response(text="after shortest wait"),
        ),
    ]
    with (
        ScriptedHTTPServer(port=0, routes={("POST", CHAT_PATH): responses}) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
    ):
        with pytest.raises(ProviderError, match=r"failed for model"):
            router.query("open cooldown on key 1")
        second = router.query("space out key 2")
        # Rotation now points at key 1 (cooling ~2 s); key 2 frees in ~0.25 s.
        third = router.query("both keys blocked")
        headers = [
            request.headers.get("Authorization")
            for request in server.recorded_requests("POST", CHAT_PATH)
        ]

    assert second.routing_trace[-1].key_id == 2
    assert second.routing_trace[-1].wait_seconds == 0.0
    final = third.routing_trace[-1]
    assert final.key_id == 2
    assert 0.0 < final.wait_seconds <= 0.25
    assert third.output_text == "after shortest wait"
    assert headers == [
        "Bearer openrouter-value-1",
        "Bearer openrouter-value-2",
        "Bearer openrouter-value-2",
    ]
