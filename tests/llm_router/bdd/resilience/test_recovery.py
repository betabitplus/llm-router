"""Bindings for provider recovery BDD scenarios."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field
from pytest_bdd import given, scenarios, then, when

from tests.llm_router.support.assertions import parse_json_object
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_error_response,
    openai_success_response,
    qwen_chat_path,
    qwen_success_response,
    run_retry_worker,
)
from tests.llm_router.support.workers.structured_recovery import (
    run_structured_recovery_worker,
)

scenarios("resilience/recovery.feature")

_OPENAI_PATH = openai_chat_path()
_QWEN_PATH = qwen_chat_path()
_RETRY_TEXT = "retry recovered"
_BAD_REQUEST = "permanent bad request"
_RECOVERY_JSON = {
    "incident_id": "INC-2048",
    "severity": "SEV2",
    "tags": ["db", "api"],
}
_INVALID_JSON = json.dumps({"incident_id": "INC-2048"})


class TicketSummary(BaseModel):
    """Structured output used by the public recovery scenario."""

    incident_id: str
    severity: str = Field(min_length=4)
    tags: list[str] = Field(min_length=2, max_length=2)


@given("a provider temporarily fails", target_fixture="case")
def provider_temporarily_fails() -> dict[str, Any]:
    return {
        "routes": {
            ("POST", _OPENAI_PATH): [
                ScriptedResponse(
                    status_code=429,
                    headers={"Content-Type": "application/json"},
                    body=openai_error_response(status_code=429, message="retry once"),
                ),
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=openai_success_response(text=_RETRY_TEXT),
                ),
            ]
        }
    }


@given("the failure is retryable")
def failure_is_retryable(case: dict[str, Any]) -> None:
    assert case["routes"]


@when("the same provider succeeds on a later attempt")
def retry_succeeds(case: dict[str, Any]) -> None:
    with ScriptedHTTPServer(port=0, routes=case["routes"]) as server:
        case["result"] = run_retry_worker(
            case="openai",
            scenario="retryable",
            server_base_url=server.base_url,
        )
        case["request_count"] = server.request_count("POST", _OPENAI_PATH)


@then("the request succeeds without route fallback")
def retry_stays_on_route(case: dict[str, Any]) -> None:
    result = case["result"]
    assert result.ok is True, result.error_message
    assert result.output_text == _RETRY_TEXT
    assert case["request_count"] == 2


@given("a provider rejects a request permanently", target_fixture="case")
def provider_rejects_permanently() -> dict[str, Any]:
    return {
        "routes": {
            ("POST", _OPENAI_PATH): [
                ScriptedResponse(
                    status_code=400,
                    headers={"Content-Type": "application/json"},
                    body=openai_error_response(
                        status_code=400,
                        message=_BAD_REQUEST,
                    ),
                ),
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=openai_success_response(text="unexpected retry"),
                ),
            ]
        }
    }


@when("the request is executed")
def execute_permanent_failure(case: dict[str, Any]) -> None:
    with ScriptedHTTPServer(port=0, routes=case["routes"]) as server:
        case["result"] = run_retry_worker(
            case="openai",
            scenario="non_retryable",
            server_base_url=server.base_url,
        )
        case["request_count"] = server.request_count("POST", _OPENAI_PATH)


@then("the provider is not retried")
def permanent_failure_is_not_retried(case: dict[str, Any]) -> None:
    result = case["result"]
    assert result.ok is False
    assert result.error_type == "ProviderError"
    assert _BAD_REQUEST in (result.error_message or "")
    assert case["request_count"] == 1


@given(
    "a provider first returns output that does not match the requested schema",
    target_fixture="case",
)
def first_structured_result_is_invalid() -> dict[str, Any]:
    return {
        "routes": {
            ("POST", _QWEN_PATH): [
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=qwen_success_response(text=_INVALID_JSON),
                ),
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=qwen_success_response(text=json.dumps(_RECOVERY_JSON)),
                ),
            ]
        }
    }


@when("a later repair attempt returns valid output")
def repair_succeeds(case: dict[str, Any]) -> None:
    with ScriptedHTTPServer(port=0, routes=case["routes"]) as server:
        case["result"] = run_structured_recovery_worker(
            case="qwenchat",
            scenario="recovery",
            server_base_url=server.base_url,
        )
        case["request_count"] = server.request_count("POST", _QWEN_PATH)


@then("the validated structured result is returned")
def structured_result_is_returned(case: dict[str, Any]) -> None:
    result = case["result"]
    assert result.ok is True, result.error_message
    parsed = TicketSummary.model_validate(parse_json_object(result.output_text))
    assert parsed == TicketSummary.model_validate(_RECOVERY_JSON)
    assert case["request_count"] == 2


@given("every repair attempt returns invalid output", target_fixture="case")
def every_repair_is_invalid() -> dict[str, Any]:
    invalid = ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=qwen_success_response(text=_INVALID_JSON),
    )
    return {"routes": {("POST", _QWEN_PATH): [invalid, invalid, invalid]}}


@when("the repair limit is reached")
def repair_limit_is_reached(case: dict[str, Any]) -> None:
    with ScriptedHTTPServer(port=0, routes=case["routes"]) as server:
        case["result"] = run_structured_recovery_worker(
            case="qwenchat",
            scenario="exhausted",
            server_base_url=server.base_url,
        )
        case["request_count"] = server.request_count("POST", _QWEN_PATH)


@then("the request fails with a public provider error")
def repair_exhaustion_is_public(case: dict[str, Any]) -> None:
    result = case["result"]
    assert result.ok is False
    assert result.error_type == "ProviderError"
    assert "Structured output validation failed" in (result.error_message or "")
    assert case["request_count"] == 3
