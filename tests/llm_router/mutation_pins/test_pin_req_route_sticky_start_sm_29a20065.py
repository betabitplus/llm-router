# mutation-pin: REQ_ROUTE_STICKY_START SM-29A20065
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router import LLMRouter, Model, Provider, ProviderLimits, RouterProfile
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_error_response,
    openai_success_response,
)
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

pytestmark = pytest.mark.verification_kind("unit")

_PATH = openai_chat_path()


@pytest.mark.verifies("REQ_ROUTE_STICKY_START[revision==1]")
@pytest.mark.parametrize("route_count", [2, 3, 4, 6])
def test_sticky_start_survives_fallback_shuffle(
    monkeypatch: pytest.MonkeyPatch, route_count: int
) -> None:
    for key_id in range(1, route_count + 1):
        monkeypatch.setenv(f"OPENROUTER_API_KEY_{key_id}", f"openrouter-key-{key_id}")
    router = LLMRouter(
        [
            RouterProfile(
                provider=Provider.OPENROUTER,
                model=Model.DEEPSEEK_V3,
                key_id=key_id,
            )
            for key_id in range(1, route_count + 1)
        ],
        round_robin_start=False,
        shuffle_fallbacks=True,
        limits_by_provider={
            Provider.OPENROUTER: ProviderLimits(
                rps=0.0,
                rpm=1_000_000.0,
                cooldown_seconds=0.0,
                cooldown_after_failures=0,
            )
        },
    )
    failure = ScriptedResponse(
        status_code=400,
        headers={"Content-Type": "application/json"},
        body=openai_error_response(status_code=400, message="first failed"),
    )
    success = ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=openai_success_response(text="ok"),
    )
    with (
        ScriptedHTTPServer(
            port=0, routes={("POST", _PATH): [failure, success, success]}
        ) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
    ):
        first = router.query("one")
        second = router.query("two")
    winner = first.routing_trace[-1]
    assert winner.error_type is None
    assert winner.route_index != 0
    assert second.routing_trace[0].route_index == winner.route_index
    assert second.routing_trace[0].key_id == winner.key_id
    assert second.routing_trace[0].error_type is None
