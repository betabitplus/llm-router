# mutation-pin: REQ_SYNC_ROUTE_FALLBACK 45f4eab791155bbe
# pinned-by: claude-opus-5-5
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


def _setup_auth(monkeypatch: pytest.MonkeyPatch, *, count: int) -> None:
    for route_id in range(1, count + 1):
        name = f"OPENROUTER_API_KEY_{route_id}"
        value = f"openrouter-auth-{route_id}"
        monkeypatch.setenv(name, value)


def _router(*, route_count: int, rps: float) -> LLMRouter:
    return LLMRouter(
        [
            RouterProfile(
                provider=Provider.OPENROUTER,
                model=Model.DEEPSEEK_V3,
                key_id=route_id,
            )
            for route_id in range(1, route_count + 1)
        ],
        round_robin_start=False,
        shuffle_fallbacks=False,
        limits_by_provider={
            Provider.OPENROUTER: ProviderLimits(
                rps=rps,
                rpm=1_000_000.0,
                cooldown_seconds=0.0,
                cooldown_after_failures=0,
            )
        },
    )


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


@pytest.mark.verifies("REQ_SYNC_ROUTE_FALLBACK[revision==2]")
def test_sync_fallback_uses_blocked_route_after_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _setup_auth(monkeypatch, count=2)
    router = _router(route_count=2, rps=10.0)
    with (
        ScriptedHTTPServer(
            port=0,
            routes={
                ("POST", _OPENAI_PATH): [
                    _success("initial-route-1"),
                    _failure("route-2-failed"),
                    _success("recovered-route-1"),
                ]
            },
        ) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
    ):
        prime_response = router.query("prime")
        assert prime_response is not None
        assert prime_response.output_text == "initial-route-1"

        response = router.query("recover")
        assert response is not None
        assert response.output_text == "recovered-route-1"
        assert response.routing_trace[0].error_type is not None
        assert response.routing_trace[-1].error_type is None
        assert response.routing_trace[-1].key_id == 1
