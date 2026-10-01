# mutation-pin: REQ_ASYNC_PROVIDER_EXECUTION FN-45935BEB
# pinned-by: delegate, one pin for 10 pins of RouterRuntime._run_async
# kills: 2f06445af49144cc 3dc1348c54023b59 4185d08c0ebf67fe 8a48c40fdfe50bce SM-230B4176
# kills: SM-AA98B36D b5451a90524408d8 c673733c4b655a92 e1a047184fcbb294 fddc853000a48d63
from __future__ import annotations

import asyncio
from dataclasses import replace
from typing import Any

import pytest

from llm_router import (
    LLMRouter,
    Model,
    Provider,
    ProviderLimits,
    RouterProfile,
    Session,
    get_config,
    install_config,
)
from tests.llm_router.support.fault_server import (
    ScriptedHTTPServer,
    ScriptedResponse,
)
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_error_response,
    openai_success_response,
    patched_openai_sdk,
    qwen_chat_path,
    qwen_success_response,
)

pytestmark = pytest.mark.verification_kind("unit")


class ZeroAttempts:
    """Non-int attempt cap that slices to zero routes."""

    def __index__(self) -> int:
        return 0


@pytest.mark.asyncio
@pytest.mark.verifies("REQ_ASYNC_PROVIDER_EXECUTION[revision==1]")
async def test_async_precall_and_failure_handling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = "mock-provider-auth-12345"
    monkeypatch.setenv("NVIDIA_API_KEY", value)

    cap: Any = ZeroAttempts()
    router_zero = LLMRouter(
        RouterProfile(model=Model.DEEPSEEK_V4_FLASH, provider=Provider.NVIDIA),
        max_attempts=cap,
    )
    with pytest.raises(TimeoutError, match=r"No route attempts were available\."):
        await router_zero.aquery("test content prompt")

    router_schema = LLMRouter(
        RouterProfile(model=Model.DEEPSEEK_V4_FLASH, provider=Provider.NVIDIA)
    )
    bad_schema = {"type": 12345, "properties": [1, 2, 3]}
    with pytest.raises(Exception, match=r"(?i)schema"):
        await router_schema.aquery("give an answer", response_schema=bad_schema)

    cooldown_limits = ProviderLimits(
        rps=1000.0,
        rpm=100000.0,
        cooldown_seconds=3600.0,
        cooldown_after_failures=1,
    )
    router_cooldown = LLMRouter(
        RouterProfile(
            model=Model.DEEPSEEK_V4_FLASH,
            provider=Provider.NVIDIA,
            attempt_timeout_seconds=1e-6,
            wait_for_cooldown_if_all_blocked=False,
            limits_by_provider={Provider.NVIDIA: cooldown_limits},
        )
    )
    with pytest.raises(Exception, match=r".*") as first:
        await router_cooldown.aquery("test content prompt")
    with pytest.raises(Exception, match=r".*") as second:
        await router_cooldown.aquery("test content prompt")
    assert str(first.value) != str(second.value)

    pace_limits = ProviderLimits(
        rps=10.0, rpm=1000.0, cooldown_seconds=0.05, cooldown_after_failures=1
    )
    router_blocked = LLMRouter(
        RouterProfile(model=Model.DEEPSEEK_V4_FLASH, provider=Provider.NVIDIA),
        default_limits=pace_limits,
        attempt_timeout_seconds=1.0,
    )
    first_res = await asyncio.gather(
        router_blocked.aquery("first"), return_exceptions=True
    )
    second_res = await asyncio.gather(
        router_blocked.aquery("second"), return_exceptions=True
    )
    assert first_res
    second_val = next(iter(second_res))
    assert not (
        isinstance(second_val, TimeoutError)
        and "No route attempts were available" in str(second_val)
    )


@pytest.mark.asyncio
@pytest.mark.verifies("REQ_ASYNC_PROVIDER_EXECUTION[revision==1]")
async def test_async_pacing_and_blocked_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = "mock-provider-auth-12345"
    for route_id in (1, 2, 3):
        monkeypatch.setenv(f"OPENROUTER_API_KEY_{route_id}", value)
    path = openai_chat_path()
    limits = {
        Provider.OPENROUTER: ProviderLimits(
            rps=2.0,
            rpm=1_000_000.0,
            cooldown_seconds=0.0,
            cooldown_after_failures=0,
        )
    }
    router = LLMRouter(
        [
            RouterProfile(
                provider=Provider.OPENROUTER,
                model=Model.DEEPSEEK_V3,
                key_id=route_id,
            )
            for route_id in (1, 2, 3)
        ],
        round_robin_start=False,
        shuffle_fallbacks=False,
        limits_by_provider=limits,
    )
    with (
        ScriptedHTTPServer(
            port=0,
            routes={
                ("POST", path): [
                    ScriptedResponse(
                        status_code=200,
                        headers={"Content-Type": "application/json"},
                        body=openai_success_response(text=marker),
                    )
                    for marker in ("A", "B", "C")
                ]
            },
        ) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
    ):
        first = await router.aquery("first prompt")
        second = await router.aquery("second prompt")
        third = await router.aquery("third prompt")

    assert [attempt.key_id for attempt in first.routing_trace] == [1]
    assert [attempt.key_id for attempt in second.routing_trace] == [1, 2]
    assert [attempt.error_type for attempt in second.routing_trace] == [
        "RouteBlockedError",
        None,
    ]
    assert 0.0 < next(iter(second.routing_trace)).wait_seconds < 1.0
    assert [attempt.route_index for attempt in third.routing_trace] == [1, 2]


@pytest.mark.asyncio
@pytest.mark.verifies("REQ_ASYNC_PROVIDER_EXECUTION[revision==1]")
async def test_async_fallback_traces_and_error_recording(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missing_env = "OPENROUTER_API_KEY_7"
    monkeypatch.delenv(missing_env, raising=False)
    for route_id in (1, 2):
        value = f"auth-{route_id}"
        monkeypatch.setenv(f"OPENROUTER_API_KEY_{route_id}", value)

    router = LLMRouter(
        [
            RouterProfile(
                provider=Provider.OPENROUTER,
                model=Model.DEEPSEEK_V3,
                key_id=7,
            ),
            RouterProfile(
                provider=Provider.OPENROUTER,
                model=Model.DEEPSEEK_V3,
                key_id=1,
            ),
            RouterProfile(
                provider=Provider.OPENROUTER,
                model=Model.DEEPSEEK_V3,
                key_id=2,
            ),
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
    failure = ScriptedResponse(
        status_code=400,
        headers={"Content-Type": "application/json"},
        body=openai_error_response(status_code=400, message="route-one-failed"),
    )
    success1 = ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=openai_success_response(text="second-route-ok"),
    )
    success2 = ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=openai_success_response(text="third-route-ok"),
    )
    with (
        ScriptedHTTPServer(
            port=0,
            routes={("POST", openai_chat_path()): [failure, success1, success2]},
        ) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
    ):
        first = await router.aquery("first")
        second = await router.aquery("second")

    assert first.output_text == "second-route-ok"
    assert len(first.routing_trace) == 3
    first_trace = first.routing_trace
    prep_attempt = next(iter(first_trace))
    assert prep_attempt.key_id == 7
    assert prep_attempt.error_type == "ApiKeyNotFoundError"
    assert prep_attempt.error_message is not None
    assert missing_env in prep_attempt.error_message

    call_attempt = next(iter(first_trace[1:]))
    assert call_attempt.key_id == 1
    assert call_attempt.error_type is not None
    assert call_attempt.error_message

    success_attempt = next(iter(reversed(first_trace)))
    assert success_attempt.key_id == 2
    assert success_attempt.error_type is None

    assert [attempt.route_index for attempt in second.routing_trace] == [2]


@pytest.mark.asyncio
@pytest.mark.verifies("REQ_ASYNC_PROVIDER_EXECUTION[revision==1]")
async def test_async_success_remembers_original_multipart_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = "mock-provider-auth-12345"
    monkeypatch.setenv("QWENCHAT_API_KEY_1", value)
    original_config = get_config()
    path = qwen_chat_path()
    parts = ["Describe the scene.", "Answer briefly."]
    session = Session(system=None)
    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", path): [
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=qwen_success_response(text="a quiet street"),
                )
            ]
        },
    ) as server:
        base_urls = dict(original_config.provider_base_urls)
        base_urls[Provider.QWENCHAT] = f"{server.base_url}/api"
        catalog = replace(original_config.catalog, provider_base_urls=base_urls)
        install_config(replace(original_config, catalog=catalog))
        router = LLMRouter(
            RouterProfile(model=Model.QWEN_MAX_LATEST, provider=Provider.QWENCHAT),
            session=session,
            temperature=0.0,
        )
        response = await router.aquery(parts)
        install_config(original_config)

    assert response.output_text == "a quiet street"
    user_turn = next(iter(session.history))
    assert user_turn.parts == tuple(parts)
