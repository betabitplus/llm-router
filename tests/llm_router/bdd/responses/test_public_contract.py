"""Bindings for the public response-contract BDD scenario."""

from __future__ import annotations

from typing import Any

from pytest_bdd import given, scenarios, then, when

from llm_router import ApiKeyNotFoundError, ConfigurationError, Model, ProviderError
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.error_boundary import run_error_boundary_inprocess
from tests.llm_router.support.workers.response_normalization import (
    run_response_normalization_dual_worker,
)
from tests.llm_router.support.workers.retry import (
    google_generate_path,
    openai_chat_path,
    openai_error_response,
    openai_success_response,
)

scenarios("responses/public_contract.feature")

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


@when("it reaches the public router boundary")
@when("the failure reaches the public router boundary")
def execute_public_error_case(case: dict[str, Any]) -> None:
    if case["scenario"] != "provider_error":
        case["result"] = run_error_boundary_inprocess(scenario=case["scenario"])
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
        case["result"] = run_error_boundary_inprocess(
            scenario="provider_error",
            server_base_url=server.base_url,
        )
        case["provider_requests"] = server.request_count("POST", _OPENAI_PATH)


def _assert_error(case: dict[str, Any], expected_type: str) -> None:
    result = case["result"]
    assert result.returncode == 0
    assert result.ok is False
    assert result.error_type == expected_type
    assert case["message"] in (result.error_message or "")


@then("it fails with a missing-key error")
def missing_key_error_is_public(case: dict[str, Any]) -> None:
    _assert_error(case, ApiKeyNotFoundError.__name__)


@then("it fails with a configuration error")
def configuration_error_is_public(case: dict[str, Any]) -> None:
    _assert_error(case, ConfigurationError.__name__)


@then("it fails with a provider error")
def provider_error_is_public(case: dict[str, Any]) -> None:
    _assert_error(case, ProviderError.__name__)
    assert case["provider_requests"] == 1
