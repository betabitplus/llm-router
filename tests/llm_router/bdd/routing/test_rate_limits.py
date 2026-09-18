"""Bindings for route availability BDD scenarios."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Iterator
from typing import Any

import pytest
from pytest_bdd import given, scenarios, then, when

from llm_router import (
    LLMRouter,
    Model,
    Provider,
    ProviderError,
    ProviderLimits,
    RouterProfile,
)
from tests.llm_router.support.fault_server import (
    ScriptedHTTPServer,
    ScriptedResponse,
    retain_fault_injection,
)
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_error_response,
    openai_success_response,
)
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

scenarios("routing/rate_limits.feature")

for _test_name, _criterion in (
    (
        "test_a_blocked_route_is_skipped_when_another_route_is_available",
        "VC_RATE_LIMIT_SKIP_BLOCKED_ROUTE",
    ),
    (
        "test_an_available_key_is_used_instead_of_waiting_for_a_blocked_key",
        "VC_RATE_LIMIT_AVAILABLE_KEY_BEFORE_WAIT",
    ),
    (
        "test_the_router_fails_immediately_when_every_route_is_blocked_and_waiting_is_disabled",
        "VC_RATE_LIMIT_ALL_BLOCKED_FAIL_FAST",
    ),
    (
        "test_the_router_waits_when_every_route_is_blocked_and_waiting_is_enabled",
        "VC_RATE_LIMIT_ALL_BLOCKED_WAIT_EARLIEST",
    ),
    (
        "test_requests_rotate_across_available_keys_before_waiting_for_reuse",
        "VC_RATE_LIMIT_AUTO_KEY_ROTATION",
    ),
):
    globals()[_test_name] = pytest.mark.coverage_item(_criterion)(globals()[_test_name])

_test_name = "test_an_available_key_is_used_instead_of_waiting_for_a_blocked_key"
globals()[_test_name] = pytest.mark.fault_item(
    "REQ_RATE_LIMIT_ROUTING",
    "interface.error-status",
)(globals()[_test_name])
del _criterion, _test_name

_SYSTEM_PROMPT = "Follow instructions exactly. Reply with only what is asked."
_NO_WAIT_MIN_WAIT_SECONDS = 5.0
_WAIT_MIN_WAIT_SECONDS = 1.0
_OPENAI_PATH = openai_chat_path()


def _keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NVIDIA_API_KEY_1", "nvidia-key-1")
    monkeypatch.setenv("NVIDIA_API_KEY_2", "nvidia-key-2")


@pytest.fixture
def local_openrouter_server(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[ScriptedHTTPServer]:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "openrouter-key-1")
    monkeypatch.setenv("OPENROUTER_API_KEY_2", "openrouter-key-2")
    with (
        ScriptedHTTPServer(
            port=0,
            routes={
                ("POST", _OPENAI_PATH): [
                    ScriptedResponse(
                        status_code=200,
                        headers={"Content-Type": "application/json"},
                        body=openai_success_response(text=marker),
                    )
                    for marker in ("A", "B", "C", "D", "E", "F")
                ]
            },
        ) as server,
        patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ),
    ):
        yield server


def _openrouter_limits(*, rps: float) -> dict[Provider, ProviderLimits]:
    return {
        Provider.OPENROUTER: ProviderLimits(
            rps=rps,
            rpm=1_000_000.0,
            cooldown_seconds=0.0,
            cooldown_after_failures=0,
        )
    }


@given("the preferred route is temporarily blocked", target_fixture="case")
def preferred_route_is_blocked(
    local_openrouter_server: ScriptedHTTPServer,
) -> dict[str, Any]:
    router = LLMRouter(
        [
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
        # Keep key 1 blocked long enough that host scheduling cannot reopen it.
        limits_by_provider=_openrouter_limits(rps=0.2),
    )
    first_response = router.query("first")
    return {
        "router": router,
        "first_response": first_response,
        "server": local_openrouter_server,
        "route_count": 2,
    }


@given("another route is available")
def another_route_is_available(case: dict[str, Any]) -> None:
    assert case["route_count"] == 2


@when("a request is made")
def request_is_made(case: dict[str, Any]) -> None:
    if case.get("public_no_wait"):
        started = time.monotonic()
        with pytest.raises(TimeoutError, match="All routes are blocked"):
            case["router"].query([_SYSTEM_PROMPT, "Reply ONLY with B."])
        case["elapsed"] = time.monotonic() - started
        return
    case["response"] = case["router"].query("second")


@then("the available route is used")
def available_route_is_used(case: dict[str, Any]) -> None:
    assert case["first_response"].routing_trace[0].key_id == 1
    assert [attempt.key_id for attempt in case["response"].routing_trace] == [1, 2]
    assert [attempt.error_type for attempt in case["response"].routing_trace] == [
        "RouteBlockedError",
        None,
    ]
    assert case["server"].request_count("POST", _OPENAI_PATH) == 2
    case["server"].retain_current_boundary_evidence()


@given("every route is temporarily blocked", target_fixture="case")
def every_route_is_blocked(
    local_openrouter_server: ScriptedHTTPServer,
) -> dict[str, Any]:
    return {"server": local_openrouter_server}


def _public_wait_router(*, wait: bool, min_wait_seconds: float) -> LLMRouter:
    return LLMRouter(
        [
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
        wait_for_cooldown_if_all_blocked=wait,
        round_robin_start=False,
        shuffle_fallbacks=False,
        limits_by_provider=_openrouter_limits(rps=1.0 / min_wait_seconds),
    )


def _block_both_routes(
    case: dict[str, Any], *, wait: bool, min_wait_seconds: float
) -> None:
    router = _public_wait_router(
        wait=wait,
        min_wait_seconds=min_wait_seconds,
    )
    first = router.query("prime route 1")
    second = router.query("prime route 2")
    assert first.routing_trace[-1].key_id == 1
    assert second.routing_trace[-1].key_id == 2
    case["router"] = router
    case["priming_responses"] = (first, second)


@given("waiting for availability is disabled")
def waiting_is_disabled(case: dict[str, Any]) -> None:
    _block_both_routes(
        case,
        wait=False,
        min_wait_seconds=_NO_WAIT_MIN_WAIT_SECONDS,
    )
    case["public_no_wait"] = True


@then("the request fails without waiting")
def blocked_request_fails_immediately(case: dict[str, Any]) -> None:
    assert case["elapsed"] < (_NO_WAIT_MIN_WAIT_SECONDS * 0.1)
    assert case["server"].request_count("POST", _OPENAI_PATH) == 2
    case["server"].retain_current_boundary_evidence()


@given("waiting for availability is enabled")
def waiting_is_enabled(case: dict[str, Any]) -> None:
    _block_both_routes(
        case,
        wait=True,
        min_wait_seconds=_WAIT_MIN_WAIT_SECONDS,
    )


@when("a route becomes available")
def route_becomes_available(case: dict[str, Any]) -> None:
    started = time.monotonic()
    case["response"] = case["router"].query("wait for earliest route")
    case["elapsed"] = time.monotonic() - started


@then("the request continues on that route")
def request_continues_after_wait(case: dict[str, Any]) -> None:
    attempt = case["response"].routing_trace[-1]
    assert case["response"].output_text == "C"
    assert attempt.provider == Provider.OPENROUTER.value
    assert attempt.key_id == 1
    assert attempt.wait_seconds > 0.0
    assert case["elapsed"] >= max(0.0, attempt.wait_seconds - 0.05)
    assert case["server"].request_count("POST", _OPENAI_PATH) == 3
    case["server"].retain_current_boundary_evidence()


@given(
    "a provider route uses automatic key selection with two keys",
    target_fixture="rotation_case",
)
def automatic_key_selection(
    local_openrouter_server: ScriptedHTTPServer,
) -> dict[str, Any]:
    router = LLMRouter(
        RouterProfile(
            provider=Provider.OPENROUTER,
            model=Model.DEEPSEEK_V3,
            key_id="auto",
        ),
        wait_for_cooldown_if_all_blocked=True,
        limits_by_provider=_openrouter_limits(rps=4.0),
    )
    return {"router": router, "server": local_openrouter_server}


@when("three asynchronous requests are made in sequence")
def make_three_async_requests(rotation_case: dict[str, Any]) -> None:
    async def run() -> tuple[Any, Any, Any, float]:
        router = rotation_case["router"]
        system = "Follow instructions exactly. Reply with only what is asked."
        first = await router.aquery(
            [system, "Reply ONLY with A."],
            temperature=0.0,
            seed=42,
        )
        second = await router.aquery(
            [system, "Reply ONLY with B."],
            temperature=0.0,
            seed=42,
        )
        started = time.monotonic()
        third = await router.aquery(
            [system, "Reply ONLY with C."],
            temperature=0.0,
            seed=42,
        )
        return first, second, third, time.monotonic() - started

    (
        rotation_case["first"],
        rotation_case["second"],
        rotation_case["third"],
        rotation_case["elapsed"],
    ) = asyncio.run(run())


@then("the first two requests use different keys")
def first_two_requests_rotate_keys(rotation_case: dict[str, Any]) -> None:
    first = rotation_case["first"]
    second = rotation_case["second"]
    assert first.output_text.strip().rstrip(".") == "A"
    assert second.output_text.strip().rstrip(".") == "B"
    assert first.routing_trace[0].key_id != second.routing_trace[0].key_id


@then("the third request waits for an available key")
def third_request_waits_for_key(rotation_case: dict[str, Any]) -> None:
    third = rotation_case["third"]
    assert third.output_text.strip().rstrip(".") == "C"
    wait_seconds = third.routing_trace[0].wait_seconds
    assert wait_seconds > 0.0
    assert rotation_case["elapsed"] >= max(0.0, wait_seconds - 0.05)
    assert rotation_case["server"].request_count("POST", _OPENAI_PATH) == 3
    rotation_case["server"].retain_current_boundary_evidence()


@given(
    "an automatic-key route with one cooled-down key and one available key",
    target_fixture="availability_case",
)
def automatic_route_with_one_blocked_key(
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, Any]:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "openrouter-key-1")
    monkeypatch.setenv("OPENROUTER_API_KEY_2", "openrouter-key-2")
    router = LLMRouter(
        RouterProfile(
            provider=Provider.OPENROUTER,
            model=Model.DEEPSEEK_V3,
            key_id="auto",
        ),
        wait_for_cooldown_if_all_blocked=False,
        limits_by_provider={
            Provider.OPENROUTER: ProviderLimits(
                rps=0.0,
                rpm=0.0,
                cooldown_seconds=30.0,
                cooldown_after_failures=1,
            )
        },
    )
    return {"router": router}


@when("a request is made while the next rotating key is still blocked")
def request_with_blocked_rotating_key(availability_case: dict[str, Any]) -> None:
    retain_fault_injection(
        contract_id="REQ_RATE_LIMIT_ROUTING",
        fault_class="interface.error-status",
        mechanism=(
            "scripted provider HTTP error opens the cooldown for one automatic key"
        ),
        details={"status_code": 400},
    )
    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", _OPENAI_PATH): [
                ScriptedResponse(
                    status_code=400,
                    headers={"Content-Type": "application/json"},
                    body=openai_error_response(
                        status_code=400,
                        message="cool down key 1",
                    ),
                ),
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=openai_success_response(text="key 2 first success"),
                ),
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=openai_success_response(
                        text="key 2 reused while key 1 blocked"
                    ),
                ),
            ]
        },
    ) as server:
        with patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ):
            with pytest.raises(ProviderError):
                availability_case["router"].query("fail key 1")
            availability_case["first_success"] = availability_case["router"].query(
                "use key 2"
            )
            started = time.monotonic()
            availability_case["second_success"] = availability_case["router"].query(
                "reuse available key"
            )
            availability_case["elapsed"] = time.monotonic() - started
        availability_case["requests"] = server.recorded_requests("POST", _OPENAI_PATH)


@then("the available key is used without waiting")
def available_key_used_without_wait(availability_case: dict[str, Any]) -> None:
    first = availability_case["first_success"]
    second = availability_case["second_success"]
    assert first.routing_trace[-1].key_id == 2
    assert second.routing_trace[-1].key_id == 2
    assert second.routing_trace[-1].wait_seconds == 0.0
    assert availability_case["elapsed"] < 1.0
    assert [
        request.headers.get("Authorization")
        for request in availability_case["requests"]
    ] == [
        "Bearer openrouter-key-1",
        "Bearer openrouter-key-2",
        "Bearer openrouter-key-2",
    ]
