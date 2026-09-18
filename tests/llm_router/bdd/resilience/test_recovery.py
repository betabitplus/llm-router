"""Bindings for provider recovery BDD scenarios."""

from __future__ import annotations

import json
from typing import Any

import pytest
from pydantic import BaseModel, Field
from pytest_bdd import given, scenarios, then, when

from tests.llm_router.support.assertions import parse_json_object
from tests.llm_router.support.fault_server import (
    ScriptedHTTPServer,
    ScriptedResponse,
    retain_fault_injection,
)
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

for _test_name, _criterion in (
    (
        "test_a_temporary_provider_failure_succeeds_on_retry",
        "VC_PROVIDER_RETRY_TRANSIENT_RECOVERY",
    ),
    (
        "test_an_asynchronous_temporary_provider_failure_succeeds_on_retry",
        "VC_PROVIDER_RETRY_TRANSIENT_RECOVERY",
    ),
    (
        "test_a_permanent_provider_failure_is_not_retried",
        "VC_PROVIDER_RETRY_PERMANENT_NO_RETRY",
    ),
    (
        "test_an_asynchronous_permanent_provider_failure_is_not_retried",
        "VC_PROVIDER_RETRY_PERMANENT_NO_RETRY",
    ),
    (
        "test_synchronous_provider_retry_stops_at_the_configured_attempt_limit",
        "VC_PROVIDER_RETRY_ATTEMPT_BOUND",
    ),
    (
        "test_asynchronous_provider_retry_stops_at_the_configured_attempt_limit",
        "VC_PROVIDER_RETRY_ATTEMPT_BOUND",
    ),
    (
        "test_invalid_structured_output_is_repaired",
        "VC_STRUCTURED_REPAIR_RECOVERY",
    ),
    (
        "test_structured_output_stops_at_a_oneattempt_budget",
        "VC_STRUCTURED_REPAIR_ATTEMPT_BOUND",
    ),
    (
        "test_structured_output_stops_at_a_twoattempt_budget",
        "VC_STRUCTURED_REPAIR_ATTEMPT_BOUND",
    ),
):
    globals()[_test_name] = pytest.mark.coverage_item(_criterion)(globals()[_test_name])

for _test_name in (
    "test_a_temporary_provider_failure_succeeds_on_retry",
    "test_an_asynchronous_temporary_provider_failure_succeeds_on_retry",
    "test_a_permanent_provider_failure_is_not_retried",
    "test_an_asynchronous_permanent_provider_failure_is_not_retried",
    "test_synchronous_provider_retry_stops_at_the_configured_attempt_limit",
    "test_asynchronous_provider_retry_stops_at_the_configured_attempt_limit",
):
    globals()[_test_name] = pytest.mark.fault_item(
        "REQ_PROVIDER_RETRY",
        "interface.error-status",
    )(globals()[_test_name])

for _test_name in (
    "test_invalid_structured_output_is_repaired",
    "test_structured_output_stops_at_a_oneattempt_budget",
    "test_structured_output_stops_at_a_twoattempt_budget",
):
    globals()[_test_name] = pytest.mark.fault_item(
        "REQ_STRUCTURED_OUTPUT_REPAIR",
        "interface.payload-schema",
    )(globals()[_test_name])

del _criterion, _test_name

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
    retain_fault_injection(
        contract_id="REQ_PROVIDER_RETRY",
        fault_class="interface.error-status",
        mechanism="scripted provider returns retryable HTTP 429 before success",
        details={"status_code": 429},
    )
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
    retain_fault_injection(
        contract_id="REQ_PROVIDER_RETRY",
        fault_class="interface.error-status",
        mechanism="scripted provider returns permanent HTTP 400",
        details={"status_code": 400},
    )
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
    assert "status code 400" in (result.error_message or "")
    assert _BAD_REQUEST not in (result.error_message or "")
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
    retain_fault_injection(
        contract_id="REQ_STRUCTURED_OUTPUT_REPAIR",
        fault_class="interface.payload-schema",
        mechanism="scripted provider returns schema-invalid structured output",
        details={"total_attempt_budget": 2},
    )
    with ScriptedHTTPServer(port=0, routes=case["routes"]) as server:
        case["result"] = run_structured_recovery_worker(
            case="qwenchat",
            scenario="recovery",
            server_base_url=server.base_url,
            max_attempts=2,
        )
        case["request_count"] = server.request_count("POST", _QWEN_PATH)


@then("the validated structured result is returned")
def structured_result_is_returned(case: dict[str, Any]) -> None:
    result = case["result"]
    assert result.ok is True, result.error_message
    parsed = TicketSummary.model_validate(parse_json_object(result.output_text))
    assert parsed == TicketSummary.model_validate(_RECOVERY_JSON)
    assert case["request_count"] == 2


@given(
    "a provider temporarily fails during asynchronous execution",
    target_fixture="case",
)
def provider_temporarily_fails_async() -> dict[str, Any]:
    return provider_temporarily_fails()


@when("the same provider succeeds on a later asynchronous attempt")
def async_retry_succeeds(case: dict[str, Any]) -> None:
    retain_fault_injection(
        contract_id="REQ_PROVIDER_RETRY",
        fault_class="interface.error-status",
        mechanism="scripted provider returns retryable HTTP 429 before async success",
        details={"status_code": 429},
    )
    with ScriptedHTTPServer(port=0, routes=case["routes"]) as server:
        case["result"] = run_retry_worker(
            case="openai",
            scenario="async_retryable",
            server_base_url=server.base_url,
        )
        case["request_count"] = server.request_count("POST", _OPENAI_PATH)


@then("the asynchronous request succeeds without route fallback")
def async_retry_stays_on_route(case: dict[str, Any]) -> None:
    retry_stays_on_route(case)


@given(
    "a provider rejects an asynchronous request permanently",
    target_fixture="case",
)
def provider_rejects_permanently_async() -> dict[str, Any]:
    return provider_rejects_permanently()


@when("the asynchronous request is executed")
def execute_permanent_failure_async(case: dict[str, Any]) -> None:
    retain_fault_injection(
        contract_id="REQ_PROVIDER_RETRY",
        fault_class="interface.error-status",
        mechanism="scripted provider returns permanent HTTP 400 during async execution",
        details={"status_code": 400},
    )
    with ScriptedHTTPServer(port=0, routes=case["routes"]) as server:
        case["result"] = run_retry_worker(
            case="openai",
            scenario="async_non_retryable",
            server_base_url=server.base_url,
        )
        case["request_count"] = server.request_count("POST", _OPENAI_PATH)


@then("the provider is not retried asynchronously")
def permanent_failure_is_not_retried_async(case: dict[str, Any]) -> None:
    permanent_failure_is_not_retried(case)


def _exhausted_retry_case() -> dict[str, Any]:
    retryable = ScriptedResponse(
        status_code=503,
        headers={"Content-Type": "application/json"},
        body=openai_error_response(status_code=503, message="still unavailable"),
    )
    sentinel = ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=openai_success_response(text="unexpected third attempt"),
    )
    return {
        "routes": {
            ("POST", _OPENAI_PATH): [retryable, retryable, sentinel],
        }
    }


@given("a provider keeps failing with retryable errors", target_fixture="case")
def provider_keeps_failing() -> dict[str, Any]:
    return _exhausted_retry_case()


@when("synchronous retry exhausts a two-attempt budget")
def sync_retry_exhausts_budget(case: dict[str, Any]) -> None:
    retain_fault_injection(
        contract_id="REQ_PROVIDER_RETRY",
        fault_class="interface.error-status",
        mechanism=(
            "scripted provider remains HTTP 503 through the full sync retry budget"
        ),
        details={"status_code": 503, "max_attempts": 2},
    )
    with ScriptedHTTPServer(port=0, routes=case["routes"]) as server:
        case["result"] = run_retry_worker(
            case="openai",
            scenario="exhausted",
            server_base_url=server.base_url,
            max_attempts=2,
        )
        case["request_count"] = server.request_count("POST", _OPENAI_PATH)


@then("exactly two synchronous provider attempts are made")
def exactly_two_sync_attempts(case: dict[str, Any]) -> None:
    result = case["result"]
    assert result.ok is False
    assert result.error_type == "ProviderError"
    assert case["request_count"] == 2


@given(
    "a provider keeps failing asynchronously with retryable errors",
    target_fixture="case",
)
def provider_keeps_failing_async() -> dict[str, Any]:
    return _exhausted_retry_case()


@when("asynchronous retry exhausts a two-attempt budget")
def async_retry_exhausts_budget(case: dict[str, Any]) -> None:
    retain_fault_injection(
        contract_id="REQ_PROVIDER_RETRY",
        fault_class="interface.error-status",
        mechanism=(
            "scripted provider remains HTTP 503 through the full async retry budget"
        ),
        details={"status_code": 503, "max_attempts": 2},
    )
    with ScriptedHTTPServer(port=0, routes=case["routes"]) as server:
        case["result"] = run_retry_worker(
            case="openai",
            scenario="async_exhausted",
            server_base_url=server.base_url,
            max_attempts=2,
        )
        case["request_count"] = server.request_count("POST", _OPENAI_PATH)


@then("exactly two asynchronous provider attempts are made")
def exactly_two_async_attempts(case: dict[str, Any]) -> None:
    exactly_two_sync_attempts(case)


@given("every structured response is invalid", target_fixture="case")
def every_structured_response_is_invalid() -> dict[str, Any]:
    invalid = ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=qwen_success_response(text=_INVALID_JSON),
    )
    return {"routes": {("POST", _QWEN_PATH): [invalid, invalid, invalid]}}


def _run_invalid_structured_budget(case: dict[str, Any], *, max_attempts: int) -> None:
    retain_fault_injection(
        contract_id="REQ_STRUCTURED_OUTPUT_REPAIR",
        fault_class="interface.payload-schema",
        mechanism="scripted provider returns schema-invalid structured output",
        details={"total_attempt_budget": max_attempts},
    )
    with ScriptedHTTPServer(port=0, routes=case["routes"]) as server:
        case["result"] = run_structured_recovery_worker(
            case="qwenchat",
            scenario="exhausted",
            server_base_url=server.base_url,
            max_attempts=max_attempts,
        )
        case["request_count"] = server.request_count("POST", _QWEN_PATH)


@when("structured output runs with a one-attempt budget")
def structured_budget_one(case: dict[str, Any]) -> None:
    _run_invalid_structured_budget(case, max_attempts=1)


@then("exactly one structured provider response is evaluated")
def exactly_one_structured_attempt(case: dict[str, Any]) -> None:
    result = case["result"]
    assert result.ok is False
    assert result.error_type == "ProviderError"
    assert "Structured output validation failed" in (result.error_message or "")
    assert case["request_count"] == 1


@when("structured output runs with a two-attempt budget")
def structured_budget_two(case: dict[str, Any]) -> None:
    _run_invalid_structured_budget(case, max_attempts=2)


@then("exactly two structured provider responses are evaluated")
def exactly_two_structured_attempts(case: dict[str, Any]) -> None:
    result = case["result"]
    assert result.ok is False
    assert result.error_type == "ProviderError"
    assert "Structured output validation failed" in (result.error_message or "")
    assert case["request_count"] == 2
