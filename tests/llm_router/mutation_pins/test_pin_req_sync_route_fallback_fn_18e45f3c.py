# mutation-pin: REQ_SYNC_ROUTE_FALLBACK FN-18E45F3C
# pinned-by: delegate, one pin for 2 pins of RouterRuntime._run_sync
# kills: 45f4eab791155bbe b4662840626becac
from __future__ import annotations

import pytest

from llm_router import (
    LLMRouter,
    Model,
    Provider,
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

_OPENAI_PATH = openai_chat_path()


def _profiles(count: int) -> list[RouterProfile]:
    return [
        RouterProfile(
            provider=Provider.OPENROUTER,
            model=Model.DEEPSEEK_V3,
            key_id=route_id,
        )
        for route_id in range(1, count + 1)
    ]


def _success(text: str) -> ScriptedResponse:
    return ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=openai_success_response(text=text),
    )


@pytest.mark.verifies("REQ_SYNC_ROUTE_FALLBACK[revision==2]")
def test_sync_fallback_after_blocked_route_and_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for route_id in (1, 2):
        monkeypatch.setenv(
            f"OPENROUTER_API_KEY_{route_id}", f"openrouter-auth-{route_id}"
        )
    router = LLMRouter(
        _profiles(2),
        round_robin_start=False,
        shuffle_fallbacks=False,
        limits_by_provider={
            Provider.OPENROUTER: ProviderLimits(
                rps=10.0,
                rpm=1_000_000.0,
                cooldown_seconds=0.0,
                cooldown_after_failures=0,
            )
        },
    )
    failure = ScriptedResponse(
        status_code=400,
        headers={"Content-Type": "application/json"},
        body=openai_error_response(status_code=400, message="route-2-failed"),
    )
    with (
        ScriptedHTTPServer(
            port=0,
            routes={
                ("POST", _OPENAI_PATH): [
                    _success("initial-route-1"),
                    failure,
                    _success("recovered-route-1"),
                ]
            },
        ) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
    ):
        prime = router.query("prime")
        assert prime is not None
        response = router.query("recover")
    assert response is not None
    assert response.output_text == "recovered-route-1"
    assert response.routing_trace[0].error_type is not None
    assert response.routing_trace[-1].error_type is None
    assert response.routing_trace[-1].key_id == 1


@pytest.mark.verifies("REQ_SYNC_ROUTE_FALLBACK[revision==2]")
def test_sync_fallback_traces_preparation_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = "mock-credential-2"
    monkeypatch.delenv("OPENROUTER_API_KEY_1", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY_2", value)
    router = LLMRouter(
        _profiles(2),
        round_robin_start=False,
        shuffle_fallbacks=False,
    )
    with (
        ScriptedHTTPServer(
            port=0,
            routes={("POST", _OPENAI_PATH): [_success("route-2-success")]},
        ) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
    ):
        response = router.query("test-prompt")
    assert response.output_text == "route-2-success"
    assert [a.route_index for a in response.routing_trace] == [0, 1]
    assert response.routing_trace[0].error_type is not None
    assert response.routing_trace[1].error_type is None
