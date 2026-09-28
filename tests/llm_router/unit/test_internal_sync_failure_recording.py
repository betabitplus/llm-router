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


def _router() -> LLMRouter:
    return LLMRouter(
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
        limits_by_provider={
            Provider.OPENROUTER: ProviderLimits(
                rps=0.0,
                rpm=0.0,
                cooldown_seconds=60.0,
                cooldown_after_failures=1,
            )
        },
    )


@pytest.mark.verifies("REQ_SYNC_ROUTE_FALLBACK[revision==2]")
def test_failed_sync_attempt_is_recorded_against_its_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The owner's decision on 2026-09-28: a failed attempt is recorded for its provider
    # and key (TREQ_RATE_LIMIT_STATE revision 2), so the failing key cools down.
    for route_id in (1, 2):
        monkeypatch.setenv(
            f"OPENROUTER_API_KEY_{route_id}", f"openrouter-auth-{route_id}"
        )
    router = _router()
    failure = ScriptedResponse(
        status_code=400,
        headers={"Content-Type": "application/json"},
        body=openai_error_response(status_code=400, message="route-1-failed"),
    )
    success = ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=openai_success_response(text="route-2"),
    )
    with (
        ScriptedHTTPServer(
            port=0,
            routes={("POST", _OPENAI_PATH): [failure, success]},
        ) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
    ):
        response = router.query("recover")

    assert response is not None
    assert response.output_text == "route-2"
    limiter = router._runtime._limiter
    assert limiter.wait_seconds(provider=Provider.OPENROUTER, key_id=1) > 0.0
    assert limiter.wait_seconds(provider=Provider.OPENROUTER, key_id=2) == 0.0
