"""Bindings for configuration override living specifications."""

from __future__ import annotations

import json
from typing import Any

from pytest_bdd import given, scenarios, then, when

from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.contract import run_contract_worker
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)

scenarios("configuration/overrides.feature")

_PATH = openai_chat_path()


def _run_public_case(*, scenario: str, response_text: str) -> dict[str, Any]:
    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", _PATH): [
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=openai_success_response(text=response_text),
                )
            ]
        },
    ) as server:
        result = run_contract_worker(
            scenario=scenario,
            server_base_url=server.base_url,
        )
        request = server.recorded_requests("POST", _PATH)[0]

    return {
        "result": result,
        "payload": json.loads(request.body.decode("utf-8")),
    }


@given("a route and router define different generation settings", target_fixture="case")
def layered_generation_settings() -> dict[str, Any]:
    return {}


@when("a request provides its own settings")
def request_overrides(case: dict[str, Any]) -> None:
    case.update(
        _run_public_case(
            scenario="layered_generation_overrides",
            response_text="precedence-ok",
        )
    )


@then("the request settings are used")
def request_settings_win(case: dict[str, Any]) -> None:
    result = case["result"]
    assert result.ok is True, result.error_message
    assert result.output_text == "precedence-ok"
    assert case["payload"]["temperature"] == 0.0
    assert result.routing_trace[0]["temperature"] == 0.0


@then("unrelated defaults are preserved")
def unrelated_defaults_survive(case: dict[str, Any]) -> None:
    result = case["result"]
    assert case["payload"]["seed"] == 7
    assert result.routing_trace[0]["seed"] == 7


@given("structured output is enabled by a default", target_fixture="case")
def structured_output_default() -> dict[str, Any]:
    return {}


@when("the request explicitly disables structured output")
def clear_structured_output(case: dict[str, Any]) -> None:
    case.update(
        _run_public_case(
            scenario="call_schema_none_clears_default",
            response_text="schema-cleared-ok",
        )
    )


@then("the request is executed without structured output")
def structured_output_is_cleared(case: dict[str, Any]) -> None:
    result = case["result"]
    assert result.ok is True, result.error_message
    assert result.output_text == "schema-cleared-ok"
    assert "response_format" not in case["payload"]
