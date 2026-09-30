# mutation-pin: REQ_CREDENTIAL_RESOLUTION e917251d85f56c41
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import pytest

from llm_router import LLMRouter, Model, Provider, ProviderLimits, RouterProfile
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
    patched_openai_sdk,
)

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_CREDENTIAL_RESOLUTION[revision==1]")
def test_auto_rotation_wraps_to_preferred_key_before_offset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prefix = "OPENROUTER_API_KEY_"
    for key_number in range(1, 10):
        monkeypatch.delenv(f"{prefix}{key_number}", raising=False)
    value = "local-route-value"
    monkeypatch.setenv(f"{prefix}2", value)

    router = LLMRouter(
        [
            RouterProfile(
                model=Model.DEEPSEEK_V3,
                provider=Provider.OPENROUTER,
                key_id="auto",
            ),
        ],
        round_robin_start=False,
        shuffle_fallbacks=False,
        temperature=0.0,
        limits_by_provider={
            Provider.OPENROUTER: ProviderLimits(
                rps=0.01,
                rpm=1_000_000.0,
                cooldown_seconds=0.0,
                cooldown_after_failures=0,
            )
        },
    )
    ok = ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=openai_success_response(text="ok"),
    )

    with (
        ScriptedHTTPServer(
            port=0,
            routes={("POST", openai_chat_path()): [ok, ok]},
        ) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
    ):
        first = router.query("first")
        monkeypatch.setenv(f"{prefix}1", value)
        second = router.query("second")

    assert [a.key_id for a in first.routing_trace] == [2]
    assert [a.key_id for a in second.routing_trace] == [1]
