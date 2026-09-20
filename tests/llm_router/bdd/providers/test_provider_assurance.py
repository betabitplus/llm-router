"""Bindings for upper-level provider-portability assurance scenarios."""

from __future__ import annotations

from typing import Any

import pytest
from pytest_bdd import given, scenarios, then, when

from llm_router import Model
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    google_error_response,
    google_generate_path,
    google_success_response,
    openai_chat_path,
    openai_error_response,
    openai_success_response,
    run_retry_worker,
)

scenarios("providers/assurance.feature")

for _test_name, _criterion, _contracts in (
    (
        "test_one_provider_route_preserves_the_public_success_and_error_boundary",
        "AC_PROVIDER_PUBLIC_SUCCESS_ERROR_STABILITY",
        (
            "REQ_RESPONSE_NORMALIZATION[revision==1]",
            "REQ_PROVIDER_ERROR_BOUNDARY[revision==1]",
        ),
    ),
    (
        "test_sync_openaicompatible_and_async_google_preserve_the_same_success_meaning",
        "AGI_PROVIDER_SYNC_ASYNC_SWAP_EQUIVALENCE",
        (
            "REQ_PROVIDER_ADAPTER_INTEROPERABILITY[revision==2]",
            "REQ_ASYNC_PROVIDER_EXECUTION[revision==1]",
            "REQ_RESPONSE_NORMALIZATION[revision==1]",
        ),
    ),
    (
        "test_a_provider_swap_preserves_success_semantics_and_a_later_failure_boundary",
        "AOV_PROVIDER_SWAP_PRESERVES_SUCCESS_FAILURE_CONTRACT",
        (
            "REQ_PROVIDER_ADAPTER_INTEROPERABILITY[revision==2]",
            "REQ_ASYNC_PROVIDER_EXECUTION[revision==1]",
            "REQ_RESPONSE_NORMALIZATION[revision==1]",
            "REQ_PROVIDER_ERROR_BOUNDARY[revision==1]",
        ),
    ),
):
    globals()[_test_name] = pytest.mark.assurance_item(_criterion)(
        globals()[_test_name]
    )
    globals()[_test_name] = pytest.mark.verifies(*_contracts)(globals()[_test_name])
    globals()[_test_name] = pytest.mark.verification_kind("bdd")(globals()[_test_name])
del _contracts, _criterion, _test_name

_OPENAI_PATH = openai_chat_path()
_GOOGLE_PATH = google_generate_path(model=Model.GEMINI_FLASH)
_EXPECTED_TEXT = "portable-ok"
_PRIVATE_DETAIL = "provider-private-detail"


def _openai_success() -> ScriptedResponse:
    return ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=openai_success_response(text=_EXPECTED_TEXT),
    )


def _openai_failure() -> ScriptedResponse:
    return ScriptedResponse(
        status_code=400,
        headers={"Content-Type": "application/json"},
        body=openai_error_response(status_code=400, message=_PRIVATE_DETAIL),
    )


def _google_success() -> ScriptedResponse:
    return ScriptedResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body=google_success_response(text=_EXPECTED_TEXT),
    )


def _google_failure() -> ScriptedResponse:
    return ScriptedResponse(
        status_code=400,
        headers={"Content-Type": "application/json"},
        body=google_error_response(status_code=400, message=_PRIVATE_DETAIL),
    )


@given(
    "an OpenAI-compatible route returns one normalized success and then rejects",
    target_fixture="case",
)
def openai_success_then_failure() -> dict[str, Any]:
    return {
        "routes": {
            ("POST", _OPENAI_PATH): [
                _openai_success(),
                _openai_failure(),
            ]
        }
    }


@when("both requests cross the public router boundary")
def execute_openai_success_then_failure(case: dict[str, Any]) -> None:
    with ScriptedHTTPServer(port=0, routes=case["routes"]) as server:
        case["success"] = run_retry_worker(
            case="openai",
            scenario="success",
            server_base_url=server.base_url,
        )
        case["count_after_success"] = server.request_count("POST", _OPENAI_PATH)
        case["failure"] = run_retry_worker(
            case="openai",
            scenario="non_retryable",
            server_base_url=server.base_url,
        )
        case["count_after_failure"] = server.request_count("POST", _OPENAI_PATH)


@then("the first request preserves the normalized success contract")
def first_request_is_normalized(case: dict[str, Any]) -> None:
    result = case["success"]
    assert result.ok is True, result.error_message
    assert result.output_text == _EXPECTED_TEXT
    assert case["count_after_success"] == 1


@then("the later rejection preserves the public provider-error contract")
def later_rejection_is_public_provider_error(case: dict[str, Any]) -> None:
    result = case["failure"]
    assert result.ok is False
    assert result.error_type == "ProviderError"
    assert _PRIVATE_DETAIL not in (result.error_message or "")
    assert case["count_after_failure"] == 2


@given(
    "equivalent OpenAI-compatible and Google success responses",
    target_fixture="case",
)
def equivalent_openai_google_successes() -> dict[str, Any]:
    return {
        "openai_routes": {("POST", _OPENAI_PATH): [_openai_success()]},
        "google_routes": {("POST", _GOOGLE_PATH): [_google_success()]},
    }


@when("the OpenAI-compatible request runs synchronously and Google runs asynchronously")
def execute_sync_openai_async_google(case: dict[str, Any]) -> None:
    with (
        ScriptedHTTPServer(port=0, routes=case["openai_routes"]) as openai_server,
        ScriptedHTTPServer(port=0, routes=case["google_routes"]) as google_server,
    ):
        case["openai"] = run_retry_worker(
            case="openai",
            scenario="success",
            server_base_url=openai_server.base_url,
        )
        case["google"] = run_retry_worker(
            case="google",
            scenario="async_success",
            server_base_url=google_server.base_url,
        )
        case["openai_count"] = openai_server.request_count("POST", _OPENAI_PATH)
        case["google_count"] = google_server.request_count("POST", _GOOGLE_PATH)


@then("both requests preserve the same public success meaning")
def sync_async_successes_match(case: dict[str, Any]) -> None:
    openai = case["openai"]
    google = case["google"]
    assert openai.ok is True, openai.error_message
    assert google.ok is True, google.error_message
    assert openai.output_text == google.output_text == _EXPECTED_TEXT
    assert case["openai_count"] == 1
    assert case["google_count"] == 1


@given(
    (
        "equivalent OpenAI-compatible and Google success responses followed by "
        "a Google rejection"
    ),
    target_fixture="case",
)
def equivalent_successes_then_google_failure() -> dict[str, Any]:
    return {
        "openai_routes": {("POST", _OPENAI_PATH): [_openai_success()]},
        "google_routes": {
            ("POST", _GOOGLE_PATH): [
                _google_success(),
                _google_failure(),
            ]
        },
    }


@when(
    "the caller executes across both provider families and then receives the rejection"
)
def execute_provider_swap_then_failure(case: dict[str, Any]) -> None:
    with (
        ScriptedHTTPServer(port=0, routes=case["openai_routes"]) as openai_server,
        ScriptedHTTPServer(port=0, routes=case["google_routes"]) as google_server,
    ):
        case["openai"] = run_retry_worker(
            case="openai",
            scenario="success",
            server_base_url=openai_server.base_url,
        )
        case["google_success"] = run_retry_worker(
            case="google",
            scenario="async_success",
            server_base_url=google_server.base_url,
        )
        case["google_failure"] = run_retry_worker(
            case="google",
            scenario="async_non_retryable",
            server_base_url=google_server.base_url,
        )
        case["openai_count"] = openai_server.request_count("POST", _OPENAI_PATH)
        case["google_count"] = google_server.request_count("POST", _GOOGLE_PATH)


@then("the successful responses preserve the same public meaning")
def provider_swap_successes_match(case: dict[str, Any]) -> None:
    openai = case["openai"]
    google = case["google_success"]
    assert openai.ok is True, openai.error_message
    assert google.ok is True, google.error_message
    assert openai.output_text == google.output_text == _EXPECTED_TEXT
    assert case["openai_count"] == 1


@then("the later Google rejection remains a public provider error")
def later_google_failure_is_public(case: dict[str, Any]) -> None:
    result = case["google_failure"]
    assert result.ok is False
    assert result.error_type == "ProviderError"
    assert _PRIVATE_DETAIL not in (result.error_message or "")
    assert case["google_count"] == 2
