"""Bindings for the public response-contract BDD scenario."""

from __future__ import annotations

from typing import Any

import pytest
from py_lib_testkit import evidence
from pytest_bdd import given, scenarios, then, when

from llm_router import ApiKeyNotFoundError, ConfigurationError, Model, ProviderError
from tests.llm_router.support.fault_server import (
    ProviderSentinelHTTPServer,
    ScriptedHTTPServer,
    ScriptedResponse,
    retain_fault_injection,
)
from tests.llm_router.support.workers.error_boundary import run_error_boundary_inprocess
from tests.llm_router.support.workers.response_normalization import (
    run_response_normalization_dual_worker,
)
from tests.llm_router.support.workers.retry import (
    google_error_response,
    google_generate_path,
    openai_chat_path,
    openai_error_response,
    openai_success_response,
    run_retry_worker,
)

scenarios("responses/public_contract.feature")

_invalid_model_test_name = (
    "test_invalid_model_configuration_surfaces_as_a_configuration_error"
)
_invalid_model_test = globals()[_invalid_model_test_name]
globals()[_invalid_model_test_name] = pytest.mark.coverage_item(
    "VC_INVALID_CONFIGURATION_PUBLIC_REJECTION"
)(_invalid_model_test)
del _invalid_model_test

_missing_key_test_name = "test_missing_credentials_surface_as_a_missingkey_error"
_missing_key_test = globals()[_missing_key_test_name]
globals()[_missing_key_test_name] = pytest.mark.coverage_item(
    "VC_CREDENTIAL_PUBLIC_MISSING_ERROR"
)(_missing_key_test)
del _missing_key_test

for _test_name, _criterion in (
    (
        "test_openaicompatible_and_google_routes_normalize_equivalent_replies_consistently",
        "VC_PROVIDER_RESPONSE_EQUIVALENCE",
    ),
    (
        "test_a_provider_http_failure_surfaces_as_a_provider_error",
        "VC_PROVIDER_ERROR_HTTP",
    ),
    (
        "test_a_provider_sdk_failure_surfaces_as_a_provider_error",
        "VC_PROVIDER_ERROR_SDK",
    ),
):
    globals()[_test_name] = pytest.mark.coverage_item(_criterion)(globals()[_test_name])

_normalization_test_name = (
    "test_openaicompatible_and_google_routes_normalize_equivalent_replies_consistently"
)
globals()[_normalization_test_name] = pytest.mark.coverage_path("Google GenAI")(
    globals()[_normalization_test_name]
)

for _test_name in (
    "test_a_provider_http_failure_surfaces_as_a_provider_error",
    "test_a_provider_sdk_failure_surfaces_as_a_provider_error",
):
    globals()[_test_name] = pytest.mark.fault_item(
        "REQ_PROVIDER_ERROR_BOUNDARY",
        "interface.error-status",
    )(globals()[_test_name])
del _criterion, _normalization_test_name, _test_name

_OPENAI_PATH = openai_chat_path()
_GOOGLE_PATH = google_generate_path(model=Model.GEMINI_FLASH)
_EXPECTED_TEXT = "parity-ok"


def _google_success_response() -> bytes:
    import json

    return json.dumps(
        {
            "candidates": [
                {
                    "index": 0,
                    "content": {"role": "model", "parts": [{"text": _EXPECTED_TEXT}]},
                    "finishReason": "STOP",
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 12,
                "candidatesTokenCount": 5,
                "totalTokenCount": 17,
            },
            "modelVersion": "local-model",
        }
    ).encode("utf-8")


@given(
    "equivalent successful responses from OpenAI-compatible and Google routes",
    target_fixture="case",
)
def equivalent_provider_responses() -> dict[str, Any]:
    return {}


@when("both responses cross the public router boundary")
def normalize_both_provider_responses(case: dict[str, Any]) -> None:
    with (
        ScriptedHTTPServer(
            port=0,
            routes={
                ("POST", _OPENAI_PATH): [
                    ScriptedResponse(
                        status_code=200,
                        headers={"Content-Type": "application/json"},
                        body=openai_success_response(text=_EXPECTED_TEXT),
                    )
                ]
            },
        ) as openai_server,
        ScriptedHTTPServer(
            port=0,
            routes={
                ("POST", _GOOGLE_PATH): [
                    ScriptedResponse(
                        status_code=200,
                        headers={"Content-Type": "application/json"},
                        body=_google_success_response(),
                    )
                ]
            },
        ) as google_server,
    ):
        case["openai"], case["google"] = run_response_normalization_dual_worker(
            openai_server_base_url=openai_server.base_url,
            google_server_base_url=google_server.base_url,
        )


@then("their visible text and usage have the same normalized shape")
def public_response_shape_matches(case: dict[str, Any]) -> None:
    openai_result = case["openai"]
    google_result = case["google"]
    assert openai_result.ok is True
    assert google_result.ok is True
    assert openai_result.output_text == google_result.output_text == _EXPECTED_TEXT
    assert (
        openai_result.usage
        == google_result.usage
        == {
            "input_tokens": 12,
            "output_tokens": 5,
            "total_tokens": 17,
        }
    )


@then("provider-specific transport details do not leak into tool fields")
def provider_transport_details_do_not_leak(case: dict[str, Any]) -> None:
    for result in (case["openai"], case["google"]):
        assert result.tool_trace == []
        assert result.tool_calls == []
        assert len(result.routing_trace) == 1
        assert result.routing_trace[0]["error_type"] is None


@given("a request has no configured API key", target_fixture="case")
def missing_api_key_case() -> dict[str, Any]:
    return {
        "scenario": "missing_api_key",
        "error_type": ApiKeyNotFoundError.__name__,
        "message": "OPENROUTER_API_KEY_1",
    }


@given("a request uses an unknown model", target_fixture="case")
def invalid_model_case() -> dict[str, Any]:
    return {
        "scenario": "invalid_model",
        "error_type": ConfigurationError.__name__,
        "message": "Unknown model",
    }


@given("a provider rejects a valid request", target_fixture="case")
def provider_error_case() -> dict[str, Any]:
    return {
        "scenario": "provider_error",
        "error_type": ProviderError.__name__,
        "message": "local bad request",
    }


@given("a provider SDK rejects a valid request", target_fixture="case")
def provider_sdk_error_case() -> dict[str, Any]:
    return {
        "scenario": "provider_sdk_error",
        "error_type": ProviderError.__name__,
        "message": "sdk private detail",
    }


@when("it reaches the public router boundary")
@when("the failure reaches the public router boundary")
def execute_public_error_case(case: dict[str, Any]) -> None:
    if case["scenario"] == "missing_api_key":
        case["result"] = run_error_boundary_inprocess(scenario=case["scenario"])
        return

    if case["scenario"] == "invalid_model":
        with ProviderSentinelHTTPServer(
            port=0,
            routes={
                ("POST", _OPENAI_PATH): [
                    ScriptedResponse(
                        status_code=500,
                        headers={"Content-Type": "application/json"},
                        body=openai_error_response(
                            status_code=500,
                            message=(
                                "provider must not be called for invalid configuration"
                            ),
                        ),
                    )
                ]
            },
        ) as server:
            case["result"] = run_error_boundary_inprocess(
                scenario=case["scenario"],
                server_base_url=server.base_url,
            )
            case["provider_requests"] = server.request_count("POST", _OPENAI_PATH)
            evidence.observation(
                "Provider boundary sentinel",
                kind="boundary-interaction-check",
                payload={
                    "boundary": "provider-http",
                    "requests_received": case["provider_requests"],
                    "interaction": (
                        "none" if case["provider_requests"] == 0 else "substitute"
                    ),
                },
            )
        return

    if case["scenario"] == "provider_sdk_error":
        with ScriptedHTTPServer(
            port=0,
            routes={
                ("POST", _GOOGLE_PATH): [
                    ScriptedResponse(
                        status_code=400,
                        headers={"Content-Type": "application/json"},
                        body=google_error_response(
                            status_code=400,
                            message=case["message"],
                        ),
                    )
                ]
            },
        ) as server:
            retain_fault_injection(
                contract_id="REQ_PROVIDER_ERROR_BOUNDARY",
                fault_class="interface.error-status",
                mechanism="Google GenAI SDK receives a provider HTTP 400 response",
            )
            case["result"] = run_retry_worker(
                case="google",
                scenario="permanent",
                server_base_url=server.base_url,
            )
            case["provider_requests"] = server.request_count("POST", _GOOGLE_PATH)
        return

    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", _OPENAI_PATH): [
                ScriptedResponse(
                    status_code=400,
                    headers={"Content-Type": "application/json"},
                    body=openai_error_response(
                        status_code=400,
                        message=case["message"],
                    ),
                )
            ]
        },
    ) as server:
        retain_fault_injection(
            contract_id="REQ_PROVIDER_ERROR_BOUNDARY",
            fault_class="interface.error-status",
            mechanism="OpenAI-compatible provider HTTP 400 response",
        )
        case["result"] = run_error_boundary_inprocess(
            scenario="provider_error",
            server_base_url=server.base_url,
        )
        case["provider_requests"] = server.request_count("POST", _OPENAI_PATH)


def _assert_error_type(case: dict[str, Any], expected_type: str) -> None:
    result = case["result"]
    assert result.returncode == 0
    assert result.ok is False
    assert result.error_type == expected_type


def _assert_error(case: dict[str, Any], expected_type: str) -> None:
    _assert_error_type(case, expected_type)
    assert case["message"] in (case["result"].error_message or "")


@then("it fails with a missing-key error")
def missing_key_error_is_public(case: dict[str, Any]) -> None:
    _assert_error(case, ApiKeyNotFoundError.__name__)


@then("it fails with a configuration error")
def configuration_error_is_public(case: dict[str, Any]) -> None:
    _assert_error(case, ConfigurationError.__name__)


@then("no provider request is sent")
def invalid_configuration_stops_before_provider(case: dict[str, Any]) -> None:
    assert case["provider_requests"] == 0


@then("it fails with a provider error")
def provider_error_is_public(case: dict[str, Any]) -> None:
    _assert_error_type(case, ProviderError.__name__)
    assert "status code 400" in (case["result"].error_message or "")
    assert case["message"] not in (case["result"].error_message or "")
    assert case["provider_requests"] == 1
