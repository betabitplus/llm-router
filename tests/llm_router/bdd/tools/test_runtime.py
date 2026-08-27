"""Bindings for tool execution BDD scenarios."""

from __future__ import annotations

from typing import Any

from pytest_bdd import given, scenarios, then, when

from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import openai_chat_path
from tests.llm_router.support.workers.tool_failure import (
    openai_tool_call_response,
    run_tool_failure_worker,
)
from tests.llm_router.support.workers.tool_round_limit import (
    run_tool_round_limit_worker,
)

scenarios("tools/runtime.feature")

_PATH = openai_chat_path()


@given("a model requests a registered tool", target_fixture="case")
def model_requests_tool() -> dict[str, Any]:
    return {
        "routes": {
            ("POST", _PATH): [
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=openai_tool_call_response(
                        tool_name="explode",
                        args={"value": 7},
                    ),
                )
            ]
        }
    }


@given("the tool fails")
def tool_fails(case: dict[str, Any]) -> None:
    assert case["routes"]


@when("the tool call is executed")
def execute_failing_tool(case: dict[str, Any]) -> None:
    with ScriptedHTTPServer(port=0, routes=case["routes"]) as server:
        case["result"] = run_tool_failure_worker(
            case="openai",
            server_base_url=server.base_url,
        )
        case["request_count"] = server.request_count("POST", _PATH)


@then("the request fails with a tool execution error")
def tool_error_is_public(case: dict[str, Any]) -> None:
    result = case["result"]
    assert result.ok is False
    assert result.error_type == "ToolExecutionError"
    assert "explode" in (result.error_message or "")
    assert "value=7" not in (result.error_message or "")


@then("no further provider turn is made")
def no_provider_turn_after_tool_failure(case: dict[str, Any]) -> None:
    assert case["request_count"] == 1


@given("the model continues requesting tools", target_fixture="case")
def model_keeps_requesting_tools() -> dict[str, Any]:
    call = ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=openai_tool_call_response(tool_name="ping", args={"value": 7}),
    )
    return {"routes": {("POST", _PATH): [call, call]}}


@when("the maximum tool round count is reached")
def reach_tool_round_limit(case: dict[str, Any]) -> None:
    with ScriptedHTTPServer(port=0, routes=case["routes"]) as server:
        case["result"] = run_tool_round_limit_worker(
            case="openai",
            server_base_url=server.base_url,
        )
        case["request_count"] = server.request_count("POST", _PATH)


@then("no additional tool round is executed")
def no_extra_tool_round(case: dict[str, Any]) -> None:
    result = case["result"]
    assert result.ok is True, result.error_message
    assert result.output_text == ""
    assert case["request_count"] == 2
    assert len(result.tool_trace) == 2


@then("the outstanding tool call remains visible in the response")
def outstanding_tool_call_is_visible(case: dict[str, Any]) -> None:
    result = case["result"]
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0]["name"] == "ping"
    assert result.tool_calls[0]["args"] == {"value": 7}
