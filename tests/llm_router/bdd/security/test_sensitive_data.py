"""Bindings for sensitive-data protection BDD scenarios."""

from __future__ import annotations

import json
import logging
from typing import Any

import pytest
from pydantic import Field, create_model
from pytest_bdd import given, scenarios, then, when

from llm_router import (
    LLMRouter,
    Model,
    Provider,
    ProviderError,
    RouterProfile,
    ToolExecutionError,
    get_config,
    install_config,
)
from tests.llm_router.support.fault_server import (
    ScriptedHTTPServer,
    ScriptedResponse,
    retain_fault_injection,
)
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_error_response,
    openai_success_response,
)
from tests.llm_router.support.workers.tool_failure import openai_tool_call_response
from tests.llm_router.support.workers.worker_patches import (
    install_fast_worker_runtime_config,
    patched_openai_sdk,
)

scenarios("security/sensitive_data.feature")

for _test_name, _criterion in (
    (
        "test_provider_failure_diagnostics_exclude_providercontrolled_protected_text",
        "VC_SECURITY_PROVIDER_FAILURE_DIAGNOSTICS",
    ),
    (
        "test_tool_failure_diagnostics_exclude_caller_and_toolcause_content",
        "VC_SECURITY_TOOL_FAILURE_DIAGNOSTICS",
    ),
    (
        "test_schema_failure_diagnostics_exclude_invalid_values_and_caller_schema_identity",
        "VC_SECURITY_SCHEMA_FAILURE_DIAGNOSTICS",
    ),
):
    globals()[_test_name] = pytest.mark.coverage_item(_criterion)(globals()[_test_name])

globals()[
    "test_provider_failure_diagnostics_exclude_providercontrolled_protected_text"
] = pytest.mark.fault_item(
    "REQ_SENSITIVE_DATA_PROTECTION",
    "interface.error-status",
)(
    globals()[
        "test_provider_failure_diagnostics_exclude_providercontrolled_protected_text"
    ]
)
globals()[
    "test_schema_failure_diagnostics_exclude_invalid_values_and_caller_schema_identity"
] = pytest.mark.fault_item(
    "REQ_SENSITIVE_DATA_PROTECTION",
    "interface.payload-schema",
)(
    globals()[
        "test_schema_failure_diagnostics_exclude_invalid_values_and_caller_schema_identity"
    ]
)

del _criterion, _test_name

_OPENAI_PATH = openai_chat_path()


def _marker(label: str) -> str:
    return f"protected-{label}-fixture"


def _render_logs(caplog: pytest.LogCaptureFixture) -> str:
    return "\n".join(
        f"{record.getMessage()} {record.msg!r} {record.__dict__!r}"
        for record in caplog.records
    )


def _event_dicts(caplog: pytest.LogCaptureFixture) -> list[dict[str, object]]:
    return [record.msg for record in caplog.records if isinstance(record.msg, dict)]


def explode(*, value: str) -> None:
    raise RuntimeError(_marker(f"tool-cause-{value}"))


@given(
    "a provider error contains protected diagnostic text and a protected credential",
    target_fixture="case",
)
def provider_error_with_protected_values(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> dict[str, Any]:
    provider_text = _marker("provider-error")
    credential = _marker("credential")
    prompt = _marker("provider-prompt")
    monkeypatch.setenv("OPENROUTER_API_KEY_1", credential)
    caplog.set_level(logging.INFO, logger="llm_router")
    return {
        "provider_text": provider_text,
        "credential": credential,
        "prompt": prompt,
        "caplog": caplog,
    }


@when("the provider failure crosses the public router boundary")
def provider_failure_crosses_public_boundary(case: dict[str, Any]) -> None:
    retain_fault_injection(
        contract_id="REQ_SENSITIVE_DATA_PROTECTION",
        fault_class="interface.error-status",
        mechanism="scripted provider returns an error body containing protected text",
        details={"status_code": 400},
    )
    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", _OPENAI_PATH): [
                ScriptedResponse(
                    status_code=400,
                    headers={"Content-Type": "application/json"},
                    body=openai_error_response(
                        status_code=400,
                        message=case["provider_text"],
                    ),
                )
            ]
        },
    ) as server:
        with (
            patched_openai_sdk(
                forced_base_url=f"{server.base_url}/v1",
                disable_sdk_retries=True,
            ),
            pytest.raises(ProviderError) as exc_info,
        ):
            LLMRouter(
                RouterProfile(
                    model=Model.DEEPSEEK_V3,
                    provider=Provider.OPENROUTER,
                )
            ).query(case["prompt"])
        case["public_error"] = str(exc_info.value)
        case["request_count"] = server.request_count("POST", _OPENAI_PATH)


@then("provider failure diagnostics contain only safe failure metadata")
def provider_failure_diagnostics_are_safe(case: dict[str, Any]) -> None:
    rendered = _render_logs(case["caplog"])
    assert case["request_count"] == 1
    for protected in (
        case["provider_text"],
        case["credential"],
        case["prompt"],
    ):
        assert protected not in case["public_error"]
        assert protected not in rendered

    failure_events = [
        event
        for event in _event_dicts(case["caplog"])
        if event.get("event_type") == "llm_router.provider.request.failed"
    ]
    assert failure_events
    assert failure_events[-1]["result_status"] == 400
    assert failure_events[-1]["error_type"] == "ProviderFailure"


@given(
    "a request contains protected prompt, credential, tool arguments, "
    "and tool-cause text",
    target_fixture="case",
)
def tool_request_with_protected_values(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> dict[str, Any]:
    prompt = _marker("tool-prompt")
    credential = _marker("credential")
    tool_argument = _marker("tool-argument")
    tool_cause = _marker(f"tool-cause-{tool_argument}")
    monkeypatch.setenv("OPENROUTER_API_KEY_1", credential)
    caplog.set_level(logging.INFO, logger="llm_router")
    return {
        "prompt": prompt,
        "credential": credential,
        "tool_argument": tool_argument,
        "tool_cause": tool_cause,
        "caplog": caplog,
    }


@when("the protected local tool fails")
def protected_local_tool_fails(case: dict[str, Any]) -> None:
    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", _OPENAI_PATH): [
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=openai_tool_call_response(
                        tool_name="explode",
                        args={"value": case["tool_argument"]},
                    ),
                )
            ]
        },
    ) as server:
        with (
            patched_openai_sdk(
                forced_base_url=f"{server.base_url}/v1",
                disable_sdk_retries=True,
            ),
            pytest.raises(ToolExecutionError) as exc_info,
        ):
            LLMRouter(
                RouterProfile(
                    model=Model.DEEPSEEK_V3,
                    provider=Provider.OPENROUTER,
                )
            ).query(
                case["prompt"],
                tools=[explode],
                tool_choice="required",
            )
        case["public_error"] = str(exc_info.value)
        case["request_count"] = server.request_count("POST", _OPENAI_PATH)


@then("tool failure diagnostics contain only safe tool metadata")
def tool_failure_diagnostics_are_safe(case: dict[str, Any]) -> None:
    rendered = _render_logs(case["caplog"])
    assert case["request_count"] == 1
    for protected in (
        case["prompt"],
        case["credential"],
        case["tool_argument"],
        case["tool_cause"],
    ):
        assert protected not in case["public_error"]
        assert protected not in rendered

    failure_events = [
        event
        for event in _event_dicts(case["caplog"])
        if event.get("event_type") == "llm_router.capability.tool.failed"
    ]
    assert failure_events
    assert failure_events[-1]["tool_name"] == "explode"
    assert failure_events[-1]["error_type"] == "ToolExecutionError"


@given(
    "structured output validation contains protected caller-controlled values",
    target_fixture="case",
)
def schema_validation_with_protected_values(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> dict[str, Any]:
    prompt = _marker("schema-prompt")
    credential = _marker("credential")
    schema_name = _marker("schema-name")
    invalid_value = _marker("invalid-value")
    monkeypatch.setenv("OPENROUTER_API_KEY_1", credential)
    caplog.set_level(logging.INFO, logger="llm_router")
    return {
        "prompt": prompt,
        "credential": credential,
        "schema_name": schema_name,
        "invalid_value": invalid_value,
        "caplog": caplog,
        "schema": create_model(
            schema_name,
            name=(str, Field(pattern="^allowed-only$")),
        ),
    }


@when("structured validation exhausts its public attempt budget")
def schema_validation_exhausts_budget(case: dict[str, Any]) -> None:
    retain_fault_injection(
        contract_id="REQ_SENSITIVE_DATA_PROTECTION",
        fault_class="interface.payload-schema",
        mechanism="scripted provider returns schema-invalid caller-controlled content",
        details={"structured_output_max_attempts": 1},
    )
    original_config = get_config()
    try:
        install_fast_worker_runtime_config(structured_output_max_attempts=1)
        with ScriptedHTTPServer(
            port=0,
            routes={
                ("POST", _OPENAI_PATH): [
                    ScriptedResponse(
                        status_code=200,
                        headers={"Content-Type": "application/json"},
                        body=openai_success_response(
                            text=json.dumps({"name": case["invalid_value"]})
                        ),
                    )
                ]
            },
        ) as server:
            with (
                patched_openai_sdk(
                    forced_base_url=f"{server.base_url}/v1",
                    disable_sdk_retries=True,
                ),
                pytest.raises(ProviderError) as exc_info,
            ):
                LLMRouter(
                    RouterProfile(
                        model=Model.DEEPSEEK_V3,
                        provider=Provider.OPENROUTER,
                    )
                ).query(
                    case["prompt"],
                    response_schema=case["schema"],
                )
            case["public_error"] = str(exc_info.value)
            case["request_count"] = server.request_count("POST", _OPENAI_PATH)
    finally:
        install_config(original_config)


@then("schema failure diagnostics contain only safe validation metadata")
def schema_failure_diagnostics_are_safe(case: dict[str, Any]) -> None:
    rendered = _render_logs(case["caplog"])
    assert case["request_count"] == 1
    assert "Structured output validation failed." in case["public_error"]
    for protected in (
        case["prompt"],
        case["credential"],
        case["schema_name"],
        case["invalid_value"],
    ):
        assert protected not in case["public_error"]
        assert protected not in rendered

    validation_events = [
        event
        for event in _event_dicts(case["caplog"])
        if event.get("event_type") == "llm_router.capability.schema.validation.failed"
    ]
    assert validation_events
    assert "schema_name" not in validation_events[-1]
    assert "error_message" not in validation_events[-1]
