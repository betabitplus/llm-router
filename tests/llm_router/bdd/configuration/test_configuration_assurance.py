"""Bindings for configuration-predictability upper assurance."""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Any

import pytest
from py_lib_testkit import evidence
from pytest_bdd import given, scenarios, then, when

from llm_router import (
    ConfigurationError,
    LLMRouter,
    Model,
    Provider,
    RouterProfile,
    get_config,
    install_config,
)
from tests.llm_router.support.fault_server import (
    ProviderSentinelHTTPServer,
    ScriptedHTTPServer,
    ScriptedResponse,
)
from tests.llm_router.support.workers.error_boundary import run_error_boundary_inprocess
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_error_response,
    openai_success_response,
)
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

scenarios("configuration/assurance.feature")

for _test_name, _criterion, _contracts in (
    (
        "test_installed_credentials_and_request_overrides_compose_predictably",
        "AC_CONFIGURATION_EFFECTIVE_VIEW_COMPOSITION",
        (
            "REQ_CONFIG_INSTALLATION_COHERENCE[revision==2]",
            "REQ_CREDENTIAL_RESOLUTION[revision==1]",
            "REQ_REQUEST_OVERRIDE_PRECEDENCE[revision==1]",
        ),
    ),
    (
        "test_invalid_requests_remain_preprovider_failures_after_installation",
        "ACV_CONFIGURATION_POST_INSTALL_REJECTION",
        (
            "REQ_CONFIG_INSTALLATION_COHERENCE[revision==2]",
            "REQ_INVALID_CONFIGURATION_ERRORS[revision==2]",
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
_RESPONSE_TEXT = "configuration-composed"
_REPLACEMENT_KEY = "configuration-assurance-key"


@given(
    "a replacement configuration and credential are ready",
    target_fixture="case",
)
def replacement_configuration_ready() -> dict[str, Any]:
    return {}


@when("a request combines router defaults route defaults and a call override")
def execute_composed_configuration(
    case: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = get_config()
    replacement_key_id = original.default_key_id + 41
    replacement = replace(original, default_key_id=replacement_key_id)
    monkeypatch.setenv(
        f"{Provider.OPENROUTER.name}_API_KEY_{replacement_key_id}",
        _REPLACEMENT_KEY,
    )

    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", _PATH): [
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=openai_success_response(text=_RESPONSE_TEXT),
                )
            ]
        },
    ) as server:
        try:
            with patched_openai_sdk(
                forced_base_url=f"{server.base_url}/v1",
                disable_sdk_retries=True,
            ):
                install_config(replacement)
                response = LLMRouter(
                    RouterProfile(
                        model=Model.DEEPSEEK_V3,
                        provider=Provider.OPENROUTER,
                        temperature=0.2,
                        seed=7,
                    ),
                    temperature=0.7,
                ).query(
                    "confirm composed configuration",
                    temperature=0.0,
                )

            recorded = server.recorded_requests("POST", _PATH)
            case["response"] = response
            case["recorded"] = recorded
            case["payload"] = json.loads(recorded[0].body.decode("utf-8"))
        finally:
            install_config(original)


@then("the provider request uses the replacement credential and call override")
def provider_sees_replacement_credential_and_override(case: dict[str, Any]) -> None:
    response = case["response"]
    recorded = case["recorded"]
    payload = case["payload"]

    assert response.output_text == _RESPONSE_TEXT
    assert len(recorded) == 1
    assert recorded[0].headers["Authorization"] == f"Bearer {_REPLACEMENT_KEY}"
    assert payload["temperature"] == 0.0
    assert response.routing_trace[0].temperature == 0.0


@then("the unrelated route default remains effective")
def route_default_survives(case: dict[str, Any]) -> None:
    response = case["response"]
    payload = case["payload"]

    assert payload["seed"] == 7
    assert response.routing_trace[0].seed == 7


@given("a valid replacement configuration is active", target_fixture="case")
def active_replacement_configuration() -> dict[str, Any]:
    return {}


@when("an unknown model is requested after installation")
def execute_invalid_request_after_install(case: dict[str, Any]) -> None:
    original = get_config()
    replacement = replace(original, default_key_id=original.default_key_id + 73)
    install_config(replacement)

    try:
        with ProviderSentinelHTTPServer(
            port=0,
            routes={
                ("POST", _PATH): [
                    ScriptedResponse(
                        status_code=500,
                        headers={"Content-Type": "application/json"},
                        body=openai_error_response(
                            status_code=500,
                            message="provider must not run after invalid configuration",
                        ),
                    )
                ]
            },
        ) as server:
            result = run_error_boundary_inprocess(
                scenario="invalid_model",
                server_base_url=server.base_url,
            )
            provider_requests = server.request_count("POST", _PATH)
            evidence.observation(
                "Provider boundary sentinel",
                kind="boundary-interaction-check",
                payload={
                    "boundary": "provider-http",
                    "requests_received": provider_requests,
                    "interaction": "none" if provider_requests == 0 else "unexpected",
                },
            )

        case["result"] = result
        case["provider_requests"] = provider_requests
        case["replacement_still_active"] = get_config() == replacement
    finally:
        install_config(original)


@then("the request fails with a public configuration error before provider execution")
def invalid_request_fails_before_provider(case: dict[str, Any]) -> None:
    result = case["result"]

    assert result.ok is False
    assert result.error_type == ConfigurationError.__name__
    assert "Unknown model" in (result.error_message or "")
    assert case["provider_requests"] == 0


@then("the replacement configuration remains active")
def replacement_remains_active(case: dict[str, Any]) -> None:
    assert case["replacement_still_active"] is True
