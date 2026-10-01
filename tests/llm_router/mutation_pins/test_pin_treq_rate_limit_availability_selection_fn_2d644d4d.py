# mutation-pin: TREQ_RATE_LIMIT_AVAILABILITY_SELECTION FN-2D644D4D
# pinned-by: delegate, one pin for 6 pins of RouterRuntime._prepare_request
# kills: 0c99e43a9ccfd476 0d1ec285e912ae10 2028da967c88aa09 87ecdb53561b826d
# kills: e92263fea0939fa2 f71e9f7973e36624
from __future__ import annotations

import pytest

from llm_router import (
    KeyId,
    LLMRouter,
    Model,
    Provider,
    ProviderError,
    ProviderLimits,
    RouterProfile,
)
from llm_router._internal.runtime.limiter import KeyResolver
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

CHAT_PATH = openai_chat_path()
# Key 2 is spaced by 0.25 s after a success; key 1 cools down for 2 s after a
# failure, so on the third request both keys are blocked and key 2 frees first.
LIMITS = ProviderLimits(
    rps=4.0,
    rpm=1_000_000.0,
    cooldown_seconds=2.0,
    cooldown_after_failures=1,
)
SPACED_LIMITS = ProviderLimits(
    rps=5.0,
    rpm=1_000_000.0,
    cooldown_seconds=0.0,
    cooldown_after_failures=0,
)


def _json_response(*, status_code: int, body: bytes) -> ScriptedResponse:
    return ScriptedResponse(
        status_code=status_code,
        headers={"Content-Type": "application/json"},
        body=body,
    )


@pytest.mark.verifies("TREQ_RATE_LIMIT_AVAILABILITY_SELECTION[revision==1]")
def test_all_blocked_auto_keys_run_shortest_wait_key_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "openrouter-value-1")
    monkeypatch.setenv("OPENROUTER_API_KEY_2", "openrouter-value-2")
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
            status_code=400,
            body=openai_error_response(status_code=400, message="cool key 1"),
        ),
        _json_response(
            status_code=200,
            body=openai_success_response(text="served by key 2"),
        ),
        _json_response(
            status_code=200,
            body=openai_success_response(text="after shortest wait"),
        ),
    ]
    with (
        ScriptedHTTPServer(port=0, routes={("POST", CHAT_PATH): responses}) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
    ):
        with pytest.raises(ProviderError, match=r"failed for model"):
            router.query("open cooldown on key 1")
        second = router.query("space out key 2")
        # Rotation points at key 1 (cooling ~2 s); key 2 frees in ~0.25 s.
        third = router.query("both keys blocked")
        headers = [
            request.headers.get("Authorization")
            for request in server.recorded_requests("POST", CHAT_PATH)
        ]

    assert second.routing_trace[-1].key_id == 2
    assert second.routing_trace[-1].wait_seconds == 0.0
    final = third.routing_trace[-1]
    assert final.key_id == 2
    assert 0.0 < final.wait_seconds <= 0.25
    assert third.output_text == "after shortest wait"
    assert headers == [
        "Bearer openrouter-value-1",
        "Bearer openrouter-value-2",
        "Bearer openrouter-value-2",
    ]


@pytest.mark.verifies("TREQ_RATE_LIMIT_AVAILABILITY_SELECTION[revision==1]")
def test_explicit_blocked_key_is_kept_without_availability_scan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "openrouter-value-1")
    monkeypatch.setenv("OPENROUTER_API_KEY_2", "openrouter-value-2")
    scanned: list[KeyId] = []
    scan = KeyResolver.candidates

    def recording_scan(
        self: KeyResolver,
        *,
        provider: Provider,
        key_id: KeyId,
    ) -> object:
        scanned.append(key_id)
        return scan(self, provider=provider, key_id=key_id)

    monkeypatch.setattr(KeyResolver, "candidates", recording_scan)
    router = LLMRouter(
        RouterProfile(
            provider=Provider.OPENROUTER,
            model=Model.DEEPSEEK_V3,
            key_id=1,
        ),
        round_robin_start=False,
        shuffle_fallbacks=False,
        wait_for_cooldown_if_all_blocked=True,
        limits_by_provider={Provider.OPENROUTER: SPACED_LIMITS},
    )
    responses = [
        _json_response(
            status_code=200,
            body=openai_success_response(text=marker),
        )
        for marker in ("A", "B")
    ]
    with (
        ScriptedHTTPServer(port=0, routes={("POST", CHAT_PATH): responses}) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
    ):
        first = router.query("first")
        # Key 1 is now blocked for about 0.2 s while key 2 was never used.
        second = router.query("second")
        headers = [
            request.headers.get("Authorization")
            for request in server.recorded_requests("POST", CHAT_PATH)
        ]

    assert first.routing_trace[-1].key_id == 1
    assert first.routing_trace[-1].wait_seconds == 0.0
    assert second.routing_trace[-1].key_id == 1
    assert second.routing_trace[-1].wait_seconds > 0.0
    assert second.output_text == "B"
    assert headers == ["Bearer openrouter-value-1"] * 2
    # An explicit key is not subject to the automatic availability scan.
    assert scanned == []
