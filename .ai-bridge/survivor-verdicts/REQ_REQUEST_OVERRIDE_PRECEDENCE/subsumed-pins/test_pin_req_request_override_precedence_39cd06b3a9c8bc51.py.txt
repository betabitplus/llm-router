# mutation-pin: REQ_REQUEST_OVERRIDE_PRECEDENCE 39cd06b3a9c8bc51
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import pytest

from llm_router import (
    LLMRouter,
    LLMRouterError,
    Model,
    Provider,
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


def _router(
    monkeypatch: pytest.MonkeyPatch, *, router_max_attempts: int | None
) -> LLMRouter:
    for route_id in (1, 2):
        monkeypatch.setenv(f"OPENROUTER_API_KEY_{route_id}", f"value-{route_id}")
    profiles = [
        RouterProfile(
            provider=Provider.OPENROUTER,
            model=Model.DEEPSEEK_V3,
            key_id=route_id,
            max_attempts=1,
        )
        for route_id in (1, 2)
    ]
    if router_max_attempts is None:
        return LLMRouter(profiles, shuffle_fallbacks=False, round_robin_start=False)
    return LLMRouter(
        profiles,
        max_attempts=router_max_attempts,
        shuffle_fallbacks=False,
        round_robin_start=False,
    )


def _responses() -> list[ScriptedResponse]:
    headers = {"Content-Type": "application/json"}
    return [
        ScriptedResponse(
            status_code=400,
            headers=headers,
            body=openai_error_response(status_code=400, message="first-failed"),
        ),
        ScriptedResponse(
            status_code=200,
            headers=headers,
            body=openai_success_response(text="second-route"),
        ),
    ]


@pytest.mark.verifies("REQ_REQUEST_OVERRIDE_PRECEDENCE[revision==1]")
def test_route_policy_default_applies_and_router_value_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    limited = _router(monkeypatch, router_max_attempts=None)
    with (
        ScriptedHTTPServer(
            port=0, routes={("POST", _OPENAI_PATH): _responses()}
        ) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1", disable_sdk_retries=True
        ),
        pytest.raises(LLMRouterError, match=r"(?s).*"),
    ):
        limited.query("hello")

    widened = _router(monkeypatch, router_max_attempts=2)
    with (
        ScriptedHTTPServer(
            port=0, routes={("POST", _OPENAI_PATH): _responses()}
        ) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1", disable_sdk_retries=True
        ),
    ):
        response = widened.query("hello")
    assert response.output_text == "second-route"
