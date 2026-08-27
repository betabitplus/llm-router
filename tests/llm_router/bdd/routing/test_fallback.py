"""Bindings for route fallback BDD scenarios."""

from __future__ import annotations

import time
from typing import Any

import pytest
from pytest_bdd import given, scenarios, then, when

from llm_router import LLMRouter, Model, Provider, ProviderLimits, RouterProfile
from llm_router._internal.runtime.router import RouterRuntime
from tests.llm_router.bdd._support import ScriptedRouteExecutor
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)
from tests.llm_router.support.workers.timeout import run_timeout_inprocess

scenarios("routing/fallback.feature")

_TIMEOUT_PATH = openai_chat_path()
_TIMEOUT_TEXT = "timeout fallback ok"
_TIMEOUT_DELAY_SECONDS = 2.0


def _profiles() -> list[RouterProfile]:
    return [
        RouterProfile(provider=Provider.GROQ, model=Model.LLAMA_SCOUT),
        RouterProfile(provider=Provider.NVIDIA, model=Model.DEEPSEEK_V4_FLASH),
        RouterProfile(provider=Provider.OPENROUTER, model=Model.DEEPSEEK_V3),
    ]


def _keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY_1", "groq-key")
    monkeypatch.setenv("NVIDIA_API_KEY_1", "nvidia-key")
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "openrouter-key")


@given("the router has two available routes", target_fixture="case")
def two_routes(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    _keys(monkeypatch)
    return {"routes": _profiles()[:2]}


@given("the first route fails")
def first_route_fails(case: dict[str, Any]) -> None:
    case["executor"] = ScriptedRouteExecutor([RuntimeError("first failed")])


@when("a request is made")
def request_is_made(case: dict[str, Any]) -> None:
    if "timeout_routes" in case:
        with ScriptedHTTPServer(port=0, routes=case["timeout_routes"]) as server:
            case["response"] = run_timeout_inprocess(
                scenario="fallback_after_timeout",
                server_base_url=server.base_url,
            )
            case["request_count"] = server.request_count("POST", _TIMEOUT_PATH)
        return

    runtime = RouterRuntime(
        spec=case["routes"],
        _executor=case["executor"],
        attempt_timeout_seconds=case.get("timeout"),
        shuffle_fallbacks=False,
        round_robin_start=False,
    )
    started = time.monotonic()
    case["response"] = runtime.query("hello")
    case["elapsed"] = time.monotonic() - started


@then("the second route is used")
def second_route_is_used(case: dict[str, Any]) -> None:
    assert case["response"].output_text == "route-1"


@then("the routing trace contains both attempts")
def both_attempts_are_visible(case: dict[str, Any]) -> None:
    assert [attempt.route_index for attempt in case["response"].routing_trace] == [0, 1]


@given("the first route exceeds its attempt timeout", target_fixture="case")
def first_route_times_out() -> dict[str, Any]:
    return {
        "timeout_routes": {
            ("POST", _TIMEOUT_PATH): [
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=openai_success_response(text="timed-out first attempt"),
                    delay_seconds=_TIMEOUT_DELAY_SECONDS,
                ),
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=openai_success_response(text=_TIMEOUT_TEXT),
                ),
            ]
        }
    }


@given("another route is available")
def another_route_is_available(case: dict[str, Any]) -> None:
    assert len(case["timeout_routes"][("POST", _TIMEOUT_PATH)]) == 2


@then("the request continues with the next route")
def timeout_falls_back(case: dict[str, Any]) -> None:
    result = case["response"]
    assert result.ok is True, result.error_message
    assert result.output_text == _TIMEOUT_TEXT
    assert case["request_count"] == 2
    assert [attempt["error_type"] for attempt in result.routing_trace] == [
        "TimeoutError",
        None,
    ]


@given("the only route exceeds its attempt timeout", target_fixture="terminal_case")
def only_route_times_out() -> dict[str, Any]:
    return {
        "routes": {
            ("POST", _TIMEOUT_PATH): [
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=openai_success_response(text="timed-out only attempt"),
                    delay_seconds=_TIMEOUT_DELAY_SECONDS,
                )
            ]
        }
    }


@when("the timed-out request is executed")
def execute_terminal_timeout(terminal_case: dict[str, Any]) -> None:
    with ScriptedHTTPServer(port=0, routes=terminal_case["routes"]) as server:
        terminal_case["result"] = run_timeout_inprocess(
            scenario="terminal_timeout",
            server_base_url=server.base_url,
        )
        terminal_case["request_count"] = server.request_count("POST", _TIMEOUT_PATH)


@then("the request fails with a timeout error")
def terminal_timeout_is_public(terminal_case: dict[str, Any]) -> None:
    result = terminal_case["result"]
    assert result.ok is False
    assert result.error_type == "TimeoutError"
    assert terminal_case["request_count"] == 1


@given(
    "more routes are available than the allowed attempt count",
    target_fixture="case",
)
def limited_attempts(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    _keys(monkeypatch)
    return {
        "routes": _profiles(),
        "executor": ScriptedRouteExecutor(
            [
                RuntimeError("first failed"),
                RuntimeError("second failed"),
                RuntimeError("third failed"),
            ]
        ),
    }


@when("all attempted routes fail")
def all_attempted_routes_fail(case: dict[str, Any]) -> None:
    runtime = RouterRuntime(
        spec=case["routes"],
        _executor=case["executor"],
        max_attempts=2,
        shuffle_fallbacks=False,
        round_robin_start=False,
    )
    with pytest.raises(RuntimeError, match="second failed"):
        runtime.query("hello")


@then("no additional routes are attempted")
def attempt_limit_is_respected(case: dict[str, Any]) -> None:
    assert len(case["executor"].requests) == 2


@given("a public router whose preferred route fails", target_fixture="public_case")
def public_router_with_failing_preferred_route() -> dict[str, Any]:
    router = LLMRouter(
        [
            RouterProfile(provider="not-a-provider", model=Model.DEEPSEEK_V4_FLASH),
            RouterProfile(provider=Provider.NVIDIA, model=Model.DEEPSEEK_V4_FLASH),
        ],
        limits_by_provider={
            Provider.NVIDIA: ProviderLimits(
                rps=0.0,
                rpm=0.0,
                cooldown_seconds=0.0,
                cooldown_after_failures=0,
            )
        },
    )
    return {"router": router}


@when("two requests are made through the same router")
def two_public_requests(public_case: dict[str, Any]) -> None:
    public_case["first_response"] = public_case["router"].query(
        [
            "Follow instructions exactly. Reply with only what is asked.",
            "Reply ONLY with OK.",
        ],
        temperature=0.0,
        seed=42,
    )
    public_case["second_response"] = public_case["router"].query(
        [
            "Follow instructions exactly. Reply with only what is asked.",
            "Reply ONLY with 12345.",
        ],
        temperature=0.0,
        seed=42,
    )


@then("the first request succeeds through fallback")
def first_request_uses_fallback(public_case: dict[str, Any]) -> None:
    response = public_case["first_response"]
    assert response.output_text.strip() == "OK"
    assert [attempt.route_index for attempt in response.routing_trace] == [0, 1]
    assert response.routing_trace[0].error_type == "ValueError"
    assert response.routing_trace[1].error_type is None


@then("the second request starts from the previously successful route")
def second_request_uses_successful_start(public_case: dict[str, Any]) -> None:
    response = public_case["second_response"]
    assert response.output_text.strip() == "12345"
    assert response.provider == Provider.NVIDIA.value
    assert len(response.routing_trace) == 1
    assert response.routing_trace[0].route_index == 1
