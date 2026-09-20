"""Bindings for upper-level resilient-execution assurance scenarios."""

from __future__ import annotations

import json
from typing import Any

import pytest
from pydantic import BaseModel, Field
from pytest_bdd import given, scenarios, then, when

from llm_router import get_config, install_config
from tests.llm_router.support.assertions import parse_json_object
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.runtime import clear_test_caches
from tests.llm_router.support.workers.retry import (
    qwen_chat_path,
    qwen_error_response,
    qwen_success_response,
)
from tests.llm_router.support.workers.structured_recovery import (
    StructuredRecoveryWorkerResult,
    run_structured_recovery_worker,
)
from tests.llm_router.support.workers.worker_patches import (
    install_fast_worker_runtime_config,
)

scenarios("resilience/assurance.feature")

for _test_name, _criterion, _contracts in (
    (
        "test_a_transient_provider_failure_during_repair_is_retried_before_recovery_succeeds",
        "AGI_RESILIENCE_RETRY_DURING_REPAIR",
        (
            "REQ_PROVIDER_RETRY[revision==2]",
            "REQ_STRUCTURED_OUTPUT_REPAIR[revision==2]",
        ),
    ),
    (
        "test_combined_retry_and_structured_budgets_stop_before_a_fifth_provider_interaction",
        "AOV_RESILIENCE_COMBINED_BUDGET_CEILING",
        (
            "REQ_PROVIDER_RETRY[revision==2]",
            "TREQ_PROVIDER_RETRY_BOUNDS[revision==1]",
            "REQ_STRUCTURED_OUTPUT_REPAIR[revision==2]",
            "TREQ_STRUCTURED_OUTPUT_ATTEMPT_BOUNDS[revision==1]",
        ),
    ),
):
    globals()[_test_name] = pytest.mark.assurance_item(_criterion)(
        globals()[_test_name]
    )
    globals()[_test_name] = pytest.mark.verifies(*_contracts)(globals()[_test_name])
    globals()[_test_name] = pytest.mark.verification_kind("bdd")(globals()[_test_name])
del _contracts, _criterion, _test_name

_QWEN_PATH = qwen_chat_path()
_VALID_JSON = {
    "incident_id": "INC-2048",
    "severity": "SEV2",
    "tags": ["db", "api"],
}
_INVALID_JSON = json.dumps({"incident_id": "INC-2048"})


class TicketSummary(BaseModel):
    """Structured output used by the composed resilience scenarios."""

    incident_id: str
    severity: str = Field(min_length=4)
    tags: list[str] = Field(min_length=2, max_length=2)


def _json_response(payload: dict[str, Any]) -> ScriptedResponse:
    return ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=qwen_success_response(text=json.dumps(payload)),
    )


def _invalid_response() -> ScriptedResponse:
    return ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=qwen_success_response(text=_INVALID_JSON),
    )


def _transient_response() -> ScriptedResponse:
    return ScriptedResponse(
        status_code=503,
        headers={"Content-Type": "application/json"},
        body=qwen_error_response(
            status_code=503,
            message="temporary provider outage",
        ),
    )


def _run_with_two_by_two_budgets(case: dict[str, Any]) -> None:
    original_config = get_config()
    try:
        clear_test_caches()
        install_fast_worker_runtime_config(retry_max_attempts=2)
        with ScriptedHTTPServer(port=0, routes=case["routes"]) as server:
            case["result"] = run_structured_recovery_worker(
                case="qwenchat",
                scenario="assurance",
                server_base_url=server.base_url,
                max_attempts=2,
            )
            case["request_count"] = server.request_count("POST", _QWEN_PATH)
            case["requests"] = server.recorded_requests("POST", _QWEN_PATH)
    finally:
        clear_test_caches()
        install_config(original_config)


@given(
    "structured recovery has started from an invalid provider response",
    target_fixture="case",
)
def structured_recovery_starts_invalid() -> dict[str, Any]:
    return {
        "routes": {
            ("POST", _QWEN_PATH): [
                _invalid_response(),
                _transient_response(),
                _json_response(_VALID_JSON),
            ]
        }
    }


@when("the repair turn transiently fails and then returns valid output")
def repair_turn_retries_then_succeeds(case: dict[str, Any]) -> None:
    _run_with_two_by_two_budgets(case)


@then("the structured request succeeds after one repair retry")
def composed_recovery_succeeds(case: dict[str, Any]) -> None:
    result = case["result"]
    assert isinstance(result, StructuredRecoveryWorkerResult)
    assert result.ok is True, result.error_message
    parsed = TicketSummary.model_validate(parse_json_object(result.output_text))
    assert parsed == TicketSummary.model_validate(_VALID_JSON)
    assert case["request_count"] == 3


@given(
    "provider retry and structured recovery each have a two-attempt budget",
    target_fixture="case",
)
def both_recovery_budgets_are_two() -> dict[str, Any]:
    return {
        "routes": {
            ("POST", _QWEN_PATH): [
                _transient_response(),
                _invalid_response(),
                _transient_response(),
                _invalid_response(),
                _json_response(_VALID_JSON),
            ]
        }
    }


@when("each structured attempt consumes one transient retry and remains invalid")
def both_structured_attempts_consume_retry(case: dict[str, Any]) -> None:
    _run_with_two_by_two_budgets(case)


@then("the request fails after exactly four provider interactions")
def combined_budget_stops_at_four(case: dict[str, Any]) -> None:
    result = case["result"]
    assert isinstance(result, StructuredRecoveryWorkerResult)
    assert result.ok is False
    assert result.error_type == "ProviderError"
    assert "Structured output validation failed" in (result.error_message or "")
    assert case["request_count"] == 4
    assert len(case["requests"]) == 4


@then("the fifth provider interaction is never made")
def fifth_provider_interaction_is_not_made(case: dict[str, Any]) -> None:
    assert case["request_count"] == 4
