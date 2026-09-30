# mutation-pin: REQ_RATE_LIMIT_ROUTING SM-04F10964
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import pytest

from llm_router import LLMRouter, Model, Provider, ProviderLimits, RouterProfile
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

pytestmark = pytest.mark.verification_kind("unit")


def _ok(text: str) -> ScriptedResponse:
    return ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=openai_success_response(text=text),
    )


@pytest.mark.verifies("REQ_RATE_LIMIT_ROUTING[revision==1]")
def test_two_free_auto_keys_rotate_between_consecutive_requests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "local-value-1")
    monkeypatch.setenv("OPENROUTER_API_KEY_2", "local-value-2")
    router = LLMRouter(
        RouterProfile(
            provider=Provider.OPENROUTER, model=Model.DEEPSEEK_V3, key_id="auto"
        ),
        wait_for_cooldown_if_all_blocked=False,
        limits_by_provider={
            Provider.OPENROUTER: ProviderLimits(
                rps=0.0, rpm=0.0, cooldown_seconds=0.0, cooldown_after_failures=0
            )
        },
    )
    with (
        ScriptedHTTPServer(
            port=0,
            routes={("POST", openai_chat_path()): [_ok("one"), _ok("two")]},
        ) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1", disable_sdk_retries=True
        ),
    ):
        first = router.query("first").routing_trace[-1].key_id
        second = router.query("second").routing_trace[-1].key_id

    assert {first, second} == {1, 2}
