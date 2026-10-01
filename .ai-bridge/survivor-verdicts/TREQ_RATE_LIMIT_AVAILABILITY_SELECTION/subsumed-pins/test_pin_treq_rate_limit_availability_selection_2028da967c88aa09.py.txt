# mutation-pin: TREQ_RATE_LIMIT_AVAILABILITY_SELECTION 2028da967c88aa09
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
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
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_error_response,
    openai_success_response,
)
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

pytestmark = pytest.mark.verification_kind("unit")


def _failure() -> ScriptedResponse:
    return ScriptedResponse(
        status_code=400,
        headers={"Content-Type": "application/json"},
        body=openai_error_response(status_code=400, message="cool down"),
    )


def _success(text: str) -> ScriptedResponse:
    return ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=openai_success_response(text=text),
    )


@pytest.mark.verifies("TREQ_RATE_LIMIT_AVAILABILITY_SELECTION[revision==1]")
def test_all_blocked_auto_key_uses_shortest_wait_not_next_rotating(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = "credential-value"
    for index in (1, 2, 3):
        monkeypatch.setenv(f"OPENROUTER_API_KEY_{index}", f"{value}-{index}")
    router = LLMRouter(
        RouterProfile(
            provider=Provider.OPENROUTER,
            model=Model.DEEPSEEK_V3,
            key_id="auto",
        ),
        wait_for_cooldown_if_all_blocked=True,
        limits_by_provider={
            Provider.OPENROUTER: ProviderLimits(
                rps=0.0,
                rpm=0.0,
                cooldown_seconds=2.0,
                cooldown_after_failures=1,
            )
        },
    )
    path = openai_chat_path()
    with (
        ScriptedHTTPServer(
            port=0,
            routes={
                ("POST", path): [
                    _failure(),
                    _success("two"),
                    _failure(),
                    _success("two again"),
                    _failure(),
                    _success("final"),
                ]
            },
        ) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
    ):
        # Keys 1, 3 and 2 enter cooldown in that order.
        with pytest.raises(ProviderError):
            router.query("fail key 1")
        assert router.query("use key 2").routing_trace[-1].key_id == 2
        with pytest.raises(ProviderError):
            router.query("fail key 3")
        assert router.query("reuse key 2").routing_trace[-1].key_id == 2
        with pytest.raises(ProviderError):
            router.query("fail key 2")
        response = router.query("all blocked")
    attempt = response.routing_trace[-1]
    # Key 3 is next in rotation, but key 1 has the shortest remaining wait.
    assert attempt.key_id == 1
    assert 0.0 < attempt.wait_seconds <= 2.0
