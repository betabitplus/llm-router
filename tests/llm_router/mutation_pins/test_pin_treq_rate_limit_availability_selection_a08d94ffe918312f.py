# mutation-pin: TREQ_RATE_LIMIT_AVAILABILITY_SELECTION a08d94ffe918312f
# pinned-by: claude-opus-5-5 and gemini-3.8-flash-high
# written-by: claude-opus-5-5, the last resort, the verdict's own model with tools
from __future__ import annotations

import pytest

from llm_router import (
    LLMRouter,
    Model,
    Provider,
    ProviderLimits,
    RouterProfile,
)
from llm_router._internal.runtime.limiter import LimiterState
from tests.llm_router.support.fault_server import (
    ScriptedHTTPServer,
    ScriptedResponse,
)
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

pytestmark = pytest.mark.verification_kind("unit")

CHAT_PATH = openai_chat_path()

LIMITS = ProviderLimits(
    rps=1_000_000.0,
    rpm=1_000_000.0,
    cooldown_seconds=0.0,
    cooldown_after_failures=0,
)

# Key 2 has been free for a quarter second longer than key 1, so a limiter
# reporting signed slack gives it a negative (still unblocked) wait.
IDLE_CREDIT_SECONDS = {2: 0.25}


def _json_response(*, status_code: int, body: bytes) -> ScriptedResponse:
    return ScriptedResponse(
        status_code=status_code,
        headers={"Content-Type": "application/json"},
        body=body,
    )


@pytest.mark.verifies("TREQ_RATE_LIMIT_AVAILABILITY_SELECTION[revision==1]")
def test_auto_selection_rotates_over_all_unblocked_keys_with_signed_waits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "openrouter-value-1")
    monkeypatch.setenv("OPENROUTER_API_KEY_2", "openrouter-value-2")
    real_wait = LimiterState.wait_seconds
    observed: list[tuple[int, float]] = []

    def signed_wait(
        self: LimiterState,
        *,
        provider: Provider | str,
        key_id: int,
        now: float | None = None,
    ) -> float:
        remaining = real_wait(self, provider=provider, key_id=key_id, now=now)
        signed = remaining - IDLE_CREDIT_SECONDS.get(key_id, 0.0)
        observed.append((key_id, signed))
        return signed

    monkeypatch.setattr(LimiterState, "wait_seconds", signed_wait)
    router = LLMRouter(
        RouterProfile(
            provider=Provider.OPENROUTER,
            model=Model.DEEPSEEK_V3,
            key_id="auto",
        ),
        round_robin_start=False,
        shuffle_fallbacks=False,
        wait_for_cooldown_if_all_blocked=True,
        limits_by_provider={Provider.OPENROUTER: LIMITS},
    )
    responses = [
        _json_response(
            status_code=200,
            body=openai_success_response(text=marker),
        )
        for marker in ("first answer", "second answer")
    ]
    with (
        ScriptedHTTPServer(port=0, routes={("POST", CHAT_PATH): responses}) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
    ):
        first = router.query("first")
        second = router.query("second")
        headers = [
            request.headers.get("Authorization")
            for request in server.recorded_requests("POST", CHAT_PATH)
        ]

    # Both keys were unblocked (non-positive waits) on the first request.
    assert (1, 0.0) in observed
    assert (2, -0.25) in observed
    # Every unblocked key stays eligible, so rotation starts at key 1 and
    # then moves on to key 2 instead of pinning the most negative wait.
    assert first.routing_trace[-1].key_id == 1
    assert first.routing_trace[-1].wait_seconds == 0.0
    assert first.output_text == "first answer"
    assert second.routing_trace[-1].key_id == 2
    assert second.output_text == "second answer"
    assert headers == [
        "Bearer openrouter-value-1",
        "Bearer openrouter-value-2",
    ]
