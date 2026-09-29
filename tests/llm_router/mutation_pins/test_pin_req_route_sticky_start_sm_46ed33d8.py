# mutation-pin: REQ_ROUTE_STICKY_START SM-46ED33D8
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


def _failure(message: str) -> ScriptedResponse:
    return ScriptedResponse(
        status_code=400,
        headers={"Content-Type": "application/json"},
        body=openai_error_response(status_code=400, message=message),
    )


def _success(text: str) -> ScriptedResponse:
    return ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=openai_success_response(text=text),
    )


@pytest.mark.verifies("REQ_ROUTE_STICKY_START[revision==1]")
def test_second_fallback_success_updates_sticky_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for key_id in range(1, 4):
        monkeypatch.setenv(f"OPENROUTER_API_KEY_{key_id}", f"openrouter-key-{key_id}")
    router = LLMRouter(
        [
            RouterProfile(
                provider=Provider.OPENROUTER,
                model=Model.DEEPSEEK_V3,
                key_id=key_id,
            )
            for key_id in range(1, 4)
        ],
        round_robin_start=False,
        shuffle_fallbacks=False,
        limits_by_provider={
            Provider.OPENROUTER: ProviderLimits(
                rps=0.0,
                rpm=1_000_000.0,
                cooldown_seconds=0.0,
                cooldown_after_failures=0,
            )
        },
    )
    with (
        ScriptedHTTPServer(
            port=0,
            routes={
                ("POST", _PATH): [
                    _failure("route 0 failed"),
                    _success("first on route 1"),
                    _failure("route 1 failed"),
                    _success("second on route 2"),
                    _success("third on route 2"),
                ]
            },
        ) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
    ):
        first = router.query("one")
        second = router.query("two")
        third = router.query("three")
    assert first.routing_trace[-1].route_index == 1
    assert second.routing_trace[0].route_index == 1
    assert second.routing_trace[-1].route_index == 2
    assert third.routing_trace[0].route_index == 2
    assert third.output_text == "third on route 2"
