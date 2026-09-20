"""Bindings for upper-level tool-orchestration assurance scenarios."""

from __future__ import annotations

import json
from typing import Any

import pytest
from pytest_bdd import given, scenarios, then, when

from llm_router import (
    LLMRouter,
    LLMRouterResponse,
    Model,
    Provider,
    RouterProfile,
    ToolExecutionError,
)
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)
from tests.llm_router.support.workers.tool_failure import openai_tool_call_response
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

scenarios("tools/assurance.feature")

for _test_name, _criterion, _contracts in (
    (
        "test_a_successful_tool_round_followed_by_a_failing_tool_stops_before_another_provider_turn",
        "AC_TOOL_EXECUTION_SUCCESS_THEN_FAILURE",
        (
            "REQ_MULTI_ROUND_TOOL_EXECUTION[revision==1]",
            "REQ_TOOL_RUNTIME_SAFETY[revision==1]",
        ),
    ),
    (
        "test_a_forced_named_tool_result_is_returned_before_the_final_provider_response",
        "AGI_TOOL_SELECTION_EXECUTION_HANDOFF",
        (
            "REQ_TOOL_CHOICE[revision==1]",
            "REQ_MULTI_ROUND_TOOL_EXECUTION[revision==1]",
        ),
    ),
):
    globals()[_test_name] = pytest.mark.assurance_item(_criterion)(
        globals()[_test_name]
    )
    globals()[_test_name] = pytest.mark.verifies(*_contracts)(globals()[_test_name])
    globals()[_test_name] = pytest.mark.verification_kind("bdd")(globals()[_test_name])
del _contracts, _criterion, _test_name

_PATH = openai_chat_path()


def add(*, a: int, b: int) -> dict[str, int]:
    """Return a+b as JSON."""
    return {"result": a + b}


def multiply(*, a: int, b: int) -> dict[str, int]:
    """Return a*b as JSON."""
    return {"result": a * b}


def explode(*, value: str) -> None:
    """Fail deterministically without exposing the argument through the public error."""
    raise RuntimeError(f"private cause: {value}")


def _router() -> LLMRouter:
    return LLMRouter(
        RouterProfile(
            provider=Provider.OPENROUTER,
            model=Model.DEEPSEEK_V3,
        ),
        temperature=0.0,
        seed=42,
    )


def _tool_messages(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        message
        for message in payload["messages"]
        if isinstance(message, dict) and message.get("role") == "tool"
    ]


@given(
    "a tool workflow succeeds once before a later local tool fails",
    target_fixture="execution_case",
)
def tool_workflow_succeeds_then_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, Any]:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "tool-assurance-key")
    return {
        "routes": {
            ("POST", _PATH): [
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=openai_tool_call_response(
                        tool_name="add",
                        args={"a": 2, "b": 3},
                    ),
                ),
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=openai_tool_call_response(
                        tool_name="explode",
                        args={"value": "protected-tool-argument"},
                    ),
                ),
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=openai_success_response(text="unexpected-third-turn"),
                ),
            ]
        }
    }


@when("the multi-round workflow is executed")
def execute_success_then_failure(execution_case: dict[str, Any]) -> None:
    with ScriptedHTTPServer(port=0, routes=execution_case["routes"]) as server:
        with (
            patched_openai_sdk(
                forced_base_url=f"{server.base_url}/v1",
                disable_sdk_retries=True,
            ),
            pytest.raises(ToolExecutionError) as error,
        ):
            _router().query(
                "Use add, then continue the tool workflow.",
                tools=[add, explode],
                tool_choice="required",
                max_tool_rounds=4,
            )
        execution_case["requests"] = server.recorded_requests("POST", _PATH)
        execution_case["request_count"] = server.request_count("POST", _PATH)
        execution_case["error"] = error.value
        server.retain_current_boundary_evidence()


@then("the first tool result reaches the next provider turn")
def first_tool_result_reaches_next_turn(execution_case: dict[str, Any]) -> None:
    requests = execution_case["requests"]
    assert len(requests) == 2
    second_payload = json.loads(requests[1].body.decode("utf-8"))
    tool_messages = _tool_messages(second_payload)
    assert len(tool_messages) == 1
    assert json.loads(tool_messages[0]["content"]) == {"result": 5}


@then("the later tool failure is public and no extra provider turn is made")
def later_tool_failure_is_bounded(execution_case: dict[str, Any]) -> None:
    error = execution_case["error"]
    assert isinstance(error, ToolExecutionError)
    assert "explode" in str(error)
    assert "protected-tool-argument" not in str(error)
    assert execution_case["request_count"] == 2


@given("a local route with add and multiply tools", target_fixture="handoff_case")
def local_route_with_two_tools(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "tool-assurance-key")
    return {}


@when("add is explicitly selected and executed")
def explicitly_select_add(handoff_case: dict[str, Any]) -> None:
    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", _PATH): [
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=openai_tool_call_response(
                        tool_name="add",
                        args={"a": 40, "b": 2},
                    ),
                ),
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=openai_success_response(text="42"),
                ),
            ]
        },
    ) as server:
        with patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ):
            response = _router().query(
                "Use the explicitly selected add tool with 40 and 2.",
                tools=[add, multiply],
                tool_choice={"type": "function", "function": {"name": "add"}},
                max_tool_rounds=2,
            )
        handoff_case["response"] = response
        handoff_case["requests"] = server.recorded_requests("POST", _PATH)
        handoff_case["request_count"] = server.request_count("POST", _PATH)
        server.retain_current_boundary_evidence()


@then("only add is executed")
def only_add_is_executed(handoff_case: dict[str, Any]) -> None:
    response = handoff_case["response"]
    assert isinstance(response, LLMRouterResponse)
    assert response.output_text == "42"
    assert [step.tool_name for step in response.tool_trace] == ["add"]
    assert handoff_case["request_count"] == 2

    first_payload = json.loads(handoff_case["requests"][0].body.decode("utf-8"))
    assert first_payload["tool_choice"]["function"]["name"] == "add"


@then("the add result reaches the final provider turn")
def add_result_reaches_final_turn(handoff_case: dict[str, Any]) -> None:
    second_payload = json.loads(handoff_case["requests"][1].body.decode("utf-8"))
    tool_messages = _tool_messages(second_payload)
    assert len(tool_messages) == 1
    assert json.loads(tool_messages[0]["content"]) == {"result": 42}
