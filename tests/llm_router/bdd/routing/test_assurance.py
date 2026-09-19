"""Bindings for upper-level routing assurance scenarios."""

from __future__ import annotations

import time
from typing import Any

import pytest
from pytest_bdd import given, scenarios, then, when

from llm_router import LLMRouter, Model, Provider, ProviderLimits, RouterProfile
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_error_response,
    openai_success_response,
)
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

scenarios("routing/assurance.feature")

for _test_name, _criterion, _requirements in (
    (
        "test_a_degraded_fallback_chain_recovers_within_the_attempt_budget",
        "ACV_ROUTE_FALLBACK_BOUNDED_RECOVERY",
        (
            "REQ_SYNC_ROUTE_FALLBACK[revision==1]",
            "REQ_ROUTE_ATTEMPT_LIMIT[revision==1]",
        ),
    ),
    (
        "test_a_blocked_preferred_route_can_still_fall_through_a_failing_route_to_success",
        "AGI_ROUTING_BLOCKED_THEN_FALLBACK",
        (
            "REQ_RATE_LIMIT_ROUTING[revision==1]",
            "REQ_SYNC_ROUTE_FALLBACK[revision==1]",
        ),
    ),
    (
        "test_recovery_remains_the_preferred_path_on_the_next_request",
        "AOV_ROUTING_PREDICTABLE_PROGRESS",
        (
            "REQ_RATE_LIMIT_ROUTING[revision==1]",
            "REQ_SYNC_ROUTE_FALLBACK[revision==1]",
            "REQ_ROUTE_STICKY_START[revision==1]",
        ),
    ),
):
    globals()[_test_name] = pytest.mark.assurance_item(_criterion)(
        globals()[_test_name]
    )
    globals()[_test_name] = pytest.mark.verifies(*_requirements)(globals()[_test_name])
    globals()[_test_name] = pytest.mark.verification_kind("bdd")(globals()[_test_name])
del _criterion, _requirements, _test_name

_OPENAI_PATH = openai_chat_path()


def _openrouter_keys(monkeypatch: pytest.MonkeyPatch, *, count: int) -> None:
    for key_id in range(1, count + 1):
        monkeypatch.setenv(
            f"OPENROUTER_API_KEY_{key_id}",
            f"openrouter-key-{key_id}",
        )


def _router(
    *,
    route_count: int,
    max_attempts: int | None = None,
    rps: float = 0.0,
) -> LLMRouter:
    return LLMRouter(
        [
            RouterProfile(
                provider=Provider.OPENROUTER,
                model=Model.DEEPSEEK_V3,
                key_id=key_id,
            )
            for key_id in range(1, route_count + 1)
        ],
        max_attempts=max_attempts,
        round_robin_start=False,
        shuffle_fallbacks=False,
        limits_by_provider={
            Provider.OPENROUTER: ProviderLimits(
                rps=rps,
                rpm=1_000_000.0,
                cooldown_seconds=0.0,
                cooldown_after_failures=0,
            )
        },
    )


def _failure(message: str) -> ScriptedResponse:
    return ScriptedResponse(
        status_code=400,
        headers={"Content-Type": "application/json"},
        body=openai_error_response(status_code=400, message=message),
    )


def _success(text: str) -> ScriptedResponse:
    return ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=openai_success_response(text=text),
    )


@given(
    "a router has four eligible routes with an attempt budget of three",
    target_fixture="bounded_case",
)
def four_routes_with_attempt_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, Any]:
    _openrouter_keys(monkeypatch, count=4)
    return {"router": _router(route_count=4, max_attempts=3)}


@given("the first two eligible routes fail")
def first_two_routes_fail(bounded_case: dict[str, Any]) -> None:
    bounded_case["failure_count"] = 2


@when("a bounded recovery request is made")
def bounded_recovery_request(bounded_case: dict[str, Any]) -> None:
    assert bounded_case["failure_count"] == 2
    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", _OPENAI_PATH): [
                _failure("route 1 failed"),
                _failure("route 2 failed"),
                _success("recovered on route 3"),
                _success("route 4 must remain untouched"),
            ]
        },
    ) as server:
        with patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ):
            bounded_case["response"] = bounded_case["router"].query("recover")
        bounded_case["request_count"] = server.request_count("POST", _OPENAI_PATH)
        server.retain_current_boundary_evidence()


@then("the third route satisfies the request")
def third_route_satisfies_request(bounded_case: dict[str, Any]) -> None:
    response = bounded_case["response"]
    assert response.output_text == "recovered on route 3"
    assert [attempt.route_index for attempt in response.routing_trace] == [0, 1, 2]
    assert response.routing_trace[-1].key_id == 3
    assert response.routing_trace[-1].error_type is None


@then("no route beyond the attempt budget is contacted")
def no_route_beyond_budget(bounded_case: dict[str, Any]) -> None:
    assert bounded_case["request_count"] == 3


@given(
    "a three-route router whose preferred route can be rate-limited",
    target_fixture="cross_case",
)
def three_route_rate_limited_router(
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, Any]:
    _openrouter_keys(monkeypatch, count=3)
    return {"router": _router(route_count=3, max_attempts=3, rps=0.2)}


@given("the next eligible route fails at the provider boundary")
def next_route_fails(cross_case: dict[str, Any]) -> None:
    cross_case["next_route_fails"] = True


@when("a cross-capability recovery request is made")
def cross_capability_recovery_request(cross_case: dict[str, Any]) -> None:
    assert cross_case["next_route_fails"] is True
    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", _OPENAI_PATH): [
                _success("prime route 1"),
                _failure("route 2 failed"),
                _success("route 3 recovered"),
            ]
        },
    ) as server:
        with patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ):
            cross_case["prime"] = cross_case["router"].query("prime")
            cross_case["response"] = cross_case["router"].query("recover")
        cross_case["requests"] = server.recorded_requests("POST", _OPENAI_PATH)
        server.retain_current_boundary_evidence()


@then("the blocked route is skipped without a provider interaction")
def blocked_route_skipped_without_provider_call(cross_case: dict[str, Any]) -> None:
    assert cross_case["prime"].routing_trace[-1].key_id == 1
    response = cross_case["response"]
    blocked = [
        attempt
        for attempt in response.routing_trace
        if attempt.key_id == 1 and attempt.error_type == "RouteBlockedError"
    ]
    assert len(blocked) == 1
    assert [
        request.headers.get("Authorization") for request in cross_case["requests"]
    ] == [
        "Bearer openrouter-key-1",
        "Bearer openrouter-key-2",
        "Bearer openrouter-key-3",
    ]


@then("routing falls through to the later eligible route")
def routing_falls_through_to_later_route(cross_case: dict[str, Any]) -> None:
    response = cross_case["response"]
    assert response.output_text == "route 3 recovered"
    assert {attempt.key_id for attempt in response.routing_trace} == {1, 2, 3}
    failed = [attempt for attempt in response.routing_trace if attempt.key_id == 2]
    succeeded = [attempt for attempt in response.routing_trace if attempt.key_id == 3]
    assert len(failed) == 1
    assert failed[0].error_type is not None
    assert len(succeeded) == 1
    assert succeeded[0].error_type is None


@given(
    "a three-route router under temporary availability degradation",
    target_fixture="outcome_case",
)
def temporarily_degraded_router(
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, Any]:
    _openrouter_keys(monkeypatch, count=3)
    return {"router": _router(route_count=3, max_attempts=3, rps=2.0)}


@given("an eligible fallback route fails before a later route succeeds")
def fallback_failure_before_success(outcome_case: dict[str, Any]) -> None:
    outcome_case["fallback_failure"] = True


@when("recovery and a follow-up request are made")
def recovery_and_follow_up(outcome_case: dict[str, Any]) -> None:
    assert outcome_case["fallback_failure"] is True
    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", _OPENAI_PATH): [
                _success("prime route 1"),
                _failure("route 2 failed"),
                _success("route 3 recovered"),
                _success("route 3 remains preferred"),
            ]
        },
    ) as server:
        with patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ):
            outcome_case["prime"] = outcome_case["router"].query("prime")
            outcome_case["recovery"] = outcome_case["router"].query("recover")
            time.sleep(0.55)
            outcome_case["follow_up"] = outcome_case["router"].query("follow up")
        outcome_case["requests"] = server.recorded_requests("POST", _OPENAI_PATH)
        server.retain_current_boundary_evidence()


@then("the degraded request still succeeds through an eligible route")
def degraded_request_succeeds(outcome_case: dict[str, Any]) -> None:
    recovery = outcome_case["recovery"]
    assert outcome_case["prime"].routing_trace[-1].key_id == 1
    assert recovery.output_text == "route 3 recovered"
    assert {attempt.key_id for attempt in recovery.routing_trace} == {1, 2, 3}
    blocked = [attempt for attempt in recovery.routing_trace if attempt.key_id == 1]
    failed = [attempt for attempt in recovery.routing_trace if attempt.key_id == 2]
    succeeded = [attempt for attempt in recovery.routing_trace if attempt.key_id == 3]
    assert len(blocked) == 1
    assert blocked[0].error_type == "RouteBlockedError"
    assert len(failed) == 1
    assert failed[0].error_type is not None
    assert len(succeeded) == 1
    assert succeeded[0].error_type is None


@then("the follow-up request starts from the recovered successful route")
def follow_up_starts_from_recovered_route(outcome_case: dict[str, Any]) -> None:
    follow_up = outcome_case["follow_up"]
    assert follow_up.output_text == "route 3 remains preferred"
    assert [attempt.key_id for attempt in follow_up.routing_trace] == [3]
    assert [
        request.headers.get("Authorization") for request in outcome_case["requests"]
    ] == [
        "Bearer openrouter-key-1",
        "Bearer openrouter-key-2",
        "Bearer openrouter-key-3",
        "Bearer openrouter-key-3",
    ]
