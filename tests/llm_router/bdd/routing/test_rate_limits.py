"""Bindings for route availability BDD scenarios."""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any

import pytest
from pytest_bdd import given, scenarios, then, when

from llm_router import LLMRouter, Model, Provider, ProviderLimits, RouterProfile
from llm_router._internal.runtime.router import RouterRuntime
from tests.llm_router.bdd._support import ScriptedRouteExecutor

scenarios("routing/rate_limits.feature")

_SYSTEM_PROMPT = "Follow instructions exactly. Reply with only what is asked."
_NO_WAIT_MIN_WAIT_SECONDS = 5.0
_WAIT_MIN_WAIT_SECONDS = 1.0


def _keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NVIDIA_API_KEY_1", "nvidia-key-1")
    monkeypatch.setenv("NVIDIA_API_KEY_2", "nvidia-key-2")


def _limits(*, rps: float) -> dict[Provider, ProviderLimits]:
    return {
        Provider.NVIDIA: ProviderLimits(
            rps=rps,
            rpm=1_000_000.0,
            cooldown_seconds=0.0,
            cooldown_after_failures=0,
        )
    }


@given("the preferred route is temporarily blocked", target_fixture="case")
def preferred_route_is_blocked(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    _keys(monkeypatch)
    executor = ScriptedRouteExecutor()
    runtime = RouterRuntime(
        spec=[
            RouterProfile(
                provider=Provider.NVIDIA,
                model=Model.DEEPSEEK_V4_FLASH,
                key_id=1,
            ),
            RouterProfile(
                provider=Provider.NVIDIA,
                model=Model.DEEPSEEK_V4_FLASH,
                key_id=2,
            ),
        ],
        _executor=executor,
        round_robin_start=False,
        shuffle_fallbacks=False,
        limits_by_provider=_limits(rps=20.0),
    )
    runtime.query("first")
    return {"runtime": runtime, "executor": executor, "route_count": 2}


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
    case["response"] = case["runtime"].query("second")


@then("the available route is used")
def available_route_is_used(case: dict[str, Any]) -> None:
    assert [request.key.key_id for request in case["executor"].requests] == [1, 2]
    assert [attempt.error_type for attempt in case["response"].routing_trace] == [
        "RouteBlockedError",
        None,
    ]


@given("every route is temporarily blocked", target_fixture="case")
def every_route_is_blocked(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    key = os.getenv("NVIDIA_API_KEY_1", "").strip() or "replay-key"
    monkeypatch.setenv("NVIDIA_API_KEY_1", key)
    return {}


def _public_wait_router(*, wait: bool, min_wait_seconds: float) -> LLMRouter:
    return LLMRouter(
        RouterProfile(
            provider=Provider.NVIDIA,
            model=Model.DEEPSEEK_V4_FLASH,
            key_id=1,
        ),
        wait_for_cooldown_if_all_blocked=wait,
        limits_by_provider={
            Provider.NVIDIA: ProviderLimits(
                rps=1.0 / min_wait_seconds,
                rpm=1_000_000_000,
                cooldown_seconds=0.0,
                cooldown_after_failures=0,
            )
        },
    )


@given("waiting for availability is disabled")
def waiting_is_disabled(case: dict[str, Any]) -> None:
    case["router"] = _public_wait_router(
        wait=False,
        min_wait_seconds=_NO_WAIT_MIN_WAIT_SECONDS,
    )
    case["first_response"] = case["router"].query(
        [_SYSTEM_PROMPT, "Reply ONLY with A."]
    )
    case["public_no_wait"] = True


@then("the request fails without waiting")
def blocked_request_fails_immediately(case: dict[str, Any]) -> None:
    assert case["first_response"].output_text.strip().rstrip(".") == "A"
    assert case["elapsed"] < (_NO_WAIT_MIN_WAIT_SECONDS * 0.1)


@given("waiting for availability is enabled")
def waiting_is_enabled(case: dict[str, Any]) -> None:
    case["router"] = _public_wait_router(
        wait=True,
        min_wait_seconds=_WAIT_MIN_WAIT_SECONDS,
    )
    case["first_response"] = case["router"].query(
        [_SYSTEM_PROMPT, "Reply ONLY with A."]
    )


@when("a route becomes available")
def route_becomes_available(case: dict[str, Any]) -> None:
    started = time.monotonic()
    case["response"] = case["router"].query([_SYSTEM_PROMPT, "Reply ONLY with B."])
    case["elapsed"] = time.monotonic() - started


@then("the request continues on that route")
def request_continues_after_wait(case: dict[str, Any]) -> None:
    assert case["first_response"].output_text.strip().rstrip(".") == "A"
    assert case["response"].output_text.strip().rstrip(".") == "B"
    attempt = case["response"].routing_trace[0]
    assert attempt.provider == Provider.NVIDIA.value
    assert attempt.key_id == 1
    assert attempt.wait_seconds > 0.0
    assert case["elapsed"] >= max(0.0, attempt.wait_seconds - 0.05)


@given(
    "a provider route uses automatic key selection with two keys",
    target_fixture="rotation_case",
)
def automatic_key_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, Any]:
    key = os.getenv("NVIDIA_API_KEY_1", "").strip() or "replay-key"
    monkeypatch.setenv("NVIDIA_API_KEY_1", key)
    monkeypatch.setenv("NVIDIA_API_KEY_2", key)
    router = LLMRouter(
        RouterProfile(
            provider=Provider.NVIDIA,
            model=Model.DEEPSEEK_V4_FLASH,
            key_id="auto",
        ),
        limits_by_provider={
            Provider.NVIDIA: ProviderLimits(
                rps=0.5,
                rpm=1_000_000_000,
                cooldown_seconds=0.0,
                cooldown_after_failures=0,
            )
        },
    )
    return {"router": router}


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
