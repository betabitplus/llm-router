"""Bindings for route fallback BDD scenarios."""

from __future__ import annotations

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
from tests.llm_router.support.workers.timeout import run_timeout_inprocess
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

scenarios("routing/fallback.feature")

for _test_name, _criterion in (
    ("test_a_failed_route_falls_back_to_the_next_route", "VC_SYNC_ROUTE_FALLBACK"),
    (
        "test_a_timedout_route_falls_back_without_waiting_for_it_indefinitely",
        "VC_ROUTE_TIMEOUT_FALLBACK",
    ),
    (
        "test_a_terminal_route_timeout_is_exposed_when_no_fallback_remains",
        "VC_ROUTE_TIMEOUT_TERMINAL",
    ),
    (
        "test_an_async_timedout_route_falls_back_to_the_next_route",
        "VC_ROUTE_TIMEOUT_FALLBACK",
    ),
    (
        "test_an_async_terminal_route_timeout_is_exposed_when_no_fallback_remains",
        "VC_ROUTE_TIMEOUT_TERMINAL",
    ),
    (
        "test_the_router_does_not_exceed_the_configured_number_of_route_attempts",
        "VC_ROUTE_ATTEMPT_LIMIT_PUBLIC_CAP",
    ),
    (
        "test_multihop_fallback_keeps_the_actual_successful_route_sticky",
        "VC_ROUTE_STICKY_MULTI_HOP",
    ),
):
    globals()[_test_name] = pytest.mark.coverage_item(_criterion)(globals()[_test_name])

for _test_name, _path_id in (
    (
        "test_a_timedout_route_falls_back_without_waiting_for_it_indefinitely",
        "sync",
    ),
    (
        "test_an_async_timedout_route_falls_back_to_the_next_route",
        "async",
    ),
    (
        "test_a_terminal_route_timeout_is_exposed_when_no_fallback_remains",
        "sync",
    ),
    (
        "test_an_async_terminal_route_timeout_is_exposed_when_no_fallback_remains",
        "async",
    ),
):
    globals()[_test_name] = pytest.mark.coverage_path(_path_id)(globals()[_test_name])

for _test_name, _contract_id, _fault_class in (
    (
        "test_a_failed_route_falls_back_to_the_next_route",
        "REQ_SYNC_ROUTE_FALLBACK",
        "interface.error-status",
    ),
    (
        "test_a_timedout_route_falls_back_without_waiting_for_it_indefinitely",
        "REQ_ROUTE_TIMEOUT_FALLBACK",
        "runtime.latency-timeout",
    ),
    (
        "test_a_terminal_route_timeout_is_exposed_when_no_fallback_remains",
        "REQ_ROUTE_TIMEOUT_FALLBACK",
        "runtime.latency-timeout",
    ),
    (
        "test_an_async_timedout_route_falls_back_to_the_next_route",
        "REQ_ROUTE_TIMEOUT_FALLBACK",
        "runtime.latency-timeout",
    ),
    (
        "test_an_async_terminal_route_timeout_is_exposed_when_no_fallback_remains",
        "REQ_ROUTE_TIMEOUT_FALLBACK",
        "runtime.latency-timeout",
    ),
):
    globals()[_test_name] = pytest.mark.fault_item(_contract_id, _fault_class)(
        globals()[_test_name]
    )
del _contract_id, _criterion, _fault_class, _path_id, _test_name

_TIMEOUT_PATH = openai_chat_path()
_TIMEOUT_TEXT = "timeout fallback ok"
_TIMEOUT_DELAY_SECONDS = 2.0


def _openrouter_keys(monkeypatch: pytest.MonkeyPatch, *, count: int) -> None:
    for key_id in range(1, count + 1):
        monkeypatch.setenv(f"OPENROUTER_API_KEY_{key_id}", f"openrouter-key-{key_id}")


@given("the router has two available routes", target_fixture="case")
def two_routes(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    _openrouter_keys(monkeypatch, count=2)
    return {
        "router": LLMRouter(
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
            shuffle_fallbacks=False,
            round_robin_start=False,
        )
    }


@given("the first route fails")
def first_route_fails(case: dict[str, Any]) -> None:
    case["first_route_status"] = 400


@when("a request is made")
def request_is_made(case: dict[str, Any]) -> None:
    if "timeout_routes" in case:
        retain_fault_injection(
            contract_id="REQ_ROUTE_TIMEOUT_FALLBACK",
            fault_class="runtime.latency-timeout",
            mechanism=(
                "scripted provider response delay exceeds "
                "the configured attempt timeout"
            ),
            details={"delay_seconds": _TIMEOUT_DELAY_SECONDS},
        )
        with ScriptedHTTPServer(port=0, routes=case["timeout_routes"]) as server:
            case["response"] = run_timeout_inprocess(
                scenario=(
                    "async_fallback_after_timeout"
                    if case.get("async_timeout")
                    else "fallback_after_timeout"
                ),
                server_base_url=server.base_url,
            )
            case["request_count"] = server.request_count("POST", _TIMEOUT_PATH)
        return

    retain_fault_injection(
        contract_id="REQ_SYNC_ROUTE_FALLBACK",
        fault_class="interface.error-status",
        mechanism=(
            "scripted provider returns an HTTP error status on the preferred route"
        ),
        details={"status_code": case["first_route_status"]},
    )
    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", _TIMEOUT_PATH): [
                ScriptedResponse(
                    status_code=case["first_route_status"],
                    headers={"Content-Type": "application/json"},
                    body=openai_error_response(
                        status_code=case["first_route_status"],
                        message="first route failed",
                    ),
                ),
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=openai_success_response(text="route-1"),
                ),
            ]
        },
    ) as server:
        with patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ):
            case["response"] = case["router"].query("hello")
        case["request_count"] = server.request_count("POST", _TIMEOUT_PATH)


@then("the second route is used")
def second_route_is_used(case: dict[str, Any]) -> None:
    assert case["response"].output_text == "route-1"
    assert case["request_count"] == 2


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


@given("the first route exceeds its async attempt timeout", target_fixture="case")
def first_route_times_out_async() -> dict[str, Any]:
    case = first_route_times_out()
    case["async_timeout"] = True
    return case


@then("the async request continues with the next route")
def async_timeout_falls_back(case: dict[str, Any]) -> None:
    timeout_falls_back(case)


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
    retain_fault_injection(
        contract_id="REQ_ROUTE_TIMEOUT_FALLBACK",
        fault_class="runtime.latency-timeout",
        mechanism=(
            "scripted provider response delay exceeds the configured attempt timeout"
        ),
        details={"delay_seconds": _TIMEOUT_DELAY_SECONDS},
    )
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
    "the only route exceeds its async attempt timeout",
    target_fixture="async_terminal_case",
)
def only_route_times_out_async() -> dict[str, Any]:
    return only_route_times_out()


@when("the async timed-out request is executed")
def execute_async_terminal_timeout(async_terminal_case: dict[str, Any]) -> None:
    retain_fault_injection(
        contract_id="REQ_ROUTE_TIMEOUT_FALLBACK",
        fault_class="runtime.latency-timeout",
        mechanism=(
            "scripted provider response delay exceeds "
            "the configured async attempt timeout"
        ),
        details={"delay_seconds": _TIMEOUT_DELAY_SECONDS},
    )
    with ScriptedHTTPServer(port=0, routes=async_terminal_case["routes"]) as server:
        async_terminal_case["result"] = run_timeout_inprocess(
            scenario="async_terminal_timeout",
            server_base_url=server.base_url,
        )
        async_terminal_case["request_count"] = server.request_count(
            "POST",
            _TIMEOUT_PATH,
        )


@then("the async request fails with a timeout error")
def async_terminal_timeout_is_public(async_terminal_case: dict[str, Any]) -> None:
    terminal_timeout_is_public(async_terminal_case)


@given(
    "more routes are available than the allowed attempt count",
    target_fixture="case",
)
def limited_attempts(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    _openrouter_keys(monkeypatch, count=3)
    return {
        "router": LLMRouter(
            [
                RouterProfile(
                    provider=Provider.OPENROUTER,
                    model=Model.DEEPSEEK_V3,
                    key_id=key_id,
                )
                for key_id in (1, 2, 3)
            ],
            max_attempts=2,
            shuffle_fallbacks=False,
            round_robin_start=False,
        )
    }


@when("all attempted routes fail")
def all_attempted_routes_fail(case: dict[str, Any]) -> None:
    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", _TIMEOUT_PATH): [
                ScriptedResponse(
                    status_code=400,
                    headers={"Content-Type": "application/json"},
                    body=openai_error_response(status_code=400, message="route failed"),
                ),
                ScriptedResponse(
                    status_code=400,
                    headers={"Content-Type": "application/json"},
                    body=openai_error_response(status_code=400, message="route failed"),
                ),
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=openai_success_response(text="third route should not run"),
                ),
            ]
        },
    ) as server:
        with (
            patched_openai_sdk(
                forced_base_url=f"{server.base_url}/v1",
                disable_sdk_retries=True,
            ),
            pytest.raises(ProviderError, match="status code 400"),
        ):
            case["router"].query("hello")
        case["request_count"] = server.request_count("POST", _TIMEOUT_PATH)


@then("no additional routes are attempted")
def attempt_limit_is_respected(case: dict[str, Any]) -> None:
    assert case["request_count"] == 2


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


@given(
    "a public router with three routes whose first two fail",
    target_fixture="multi_hop_case",
)
def public_router_with_two_failing_routes(
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, Any]:
    _openrouter_keys(monkeypatch, count=3)
    return {
        "router": LLMRouter(
            [
                RouterProfile(
                    provider=Provider.OPENROUTER,
                    model=Model.DEEPSEEK_V3,
                    key_id=key_id,
                )
                for key_id in (1, 2, 3)
            ],
            round_robin_start=True,
            shuffle_fallbacks=False,
            limits_by_provider={
                Provider.OPENROUTER: ProviderLimits(
                    rps=0.0,
                    rpm=0.0,
                    cooldown_seconds=0.0,
                    cooldown_after_failures=0,
                )
            },
        )
    }


@when("two requests are made after multi-hop fallback")
def two_requests_after_multi_hop_fallback(multi_hop_case: dict[str, Any]) -> None:
    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", _TIMEOUT_PATH): [
                ScriptedResponse(
                    status_code=400,
                    headers={"Content-Type": "application/json"},
                    body=openai_error_response(
                        status_code=400, message="route 0 failed"
                    ),
                ),
                ScriptedResponse(
                    status_code=400,
                    headers={"Content-Type": "application/json"},
                    body=openai_error_response(
                        status_code=400, message="route 1 failed"
                    ),
                ),
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=openai_success_response(text="third route"),
                ),
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=openai_success_response(text="sticky third route"),
                ),
            ]
        },
    ) as server:
        with patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ):
            multi_hop_case["first_response"] = multi_hop_case["router"].query("first")
            multi_hop_case["second_response"] = multi_hop_case["router"].query("second")
        multi_hop_case["request_count"] = server.request_count("POST", _TIMEOUT_PATH)


@then("the first request succeeds on the third route")
def first_request_succeeds_on_third_route(multi_hop_case: dict[str, Any]) -> None:
    response = multi_hop_case["first_response"]
    assert response.output_text == "third route"
    assert [attempt.route_index for attempt in response.routing_trace] == [0, 1, 2]
    assert [attempt.key_id for attempt in response.routing_trace] == [1, 2, 3]


@then("the second request starts from the third route")
def second_request_starts_from_third_route(multi_hop_case: dict[str, Any]) -> None:
    response = multi_hop_case["second_response"]
    assert response.output_text == "sticky third route"
    assert [attempt.route_index for attempt in response.routing_trace] == [2]
    assert [attempt.key_id for attempt in response.routing_trace] == [3]
    assert multi_hop_case["request_count"] == 4
