# %%
"""Bindings for the multi-round tool execution BDD scenario."""

from __future__ import annotations

import json

import pytest
from py_lib_testkit import evidence
from pydantic import BaseModel, Field, create_model
from pytest_bdd import given, parsers, scenarios, then, when

from llm_router import LLMRouter, LLMRouterResponse, Model, Provider, RouterProfile
from tests.llm_router.bdd._support import prepare_gemini_webapi_runtime
from tests.llm_router.support.assertions import parse_json_object
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)
from tests.llm_router.support.workers.tool_failure import openai_tool_call_response
from tests.llm_router.support.workers.worker_patches import patched_openai_sdk

scenarios("tools/multi_round.feature")

for _test_name, _criterion in (
    (
        "test_a_provider_route_completes_a_twostep_calculation_with_tools",
        "VC_TOOL_MULTI_ROUND_REPLAY_FAMILIES",
    ),
    (
        "test_google_genai_uses_a_profilelevel_tool_in_a_structured_workflow",
        "VC_TOOL_MULTI_ROUND_REPLAY_FAMILIES",
    ),
    (
        "test_openaicompatible_completes_the_multiround_workflow_at_a_local_boundary",
        "VC_TOOL_MULTI_ROUND_OPENAI_LOCAL",
    ),
):
    globals()[_test_name] = pytest.mark.coverage_item(_criterion)(globals()[_test_name])

for _test_name, _path_id in (
    (
        "test_a_provider_route_completes_a_twostep_calculation_with_tools",
        "example:route",
    ),
    (
        "test_google_genai_uses_a_profilelevel_tool_in_a_structured_workflow",
        "Google GenAI",
    ),
    (
        "test_openaicompatible_completes_the_multiround_workflow_at_a_local_boundary",
        "OpenAI-compatible",
    ),
):
    globals()[_test_name] = pytest.mark.coverage_path(_path_id)(globals()[_test_name])
del _criterion, _path_id, _test_name

_SYSTEM_PROMPT = "Follow instructions exactly. Reply with only what is asked."
_PROFILE_TOOL_PROMPT = (
    "You have a tool named multiply(a, b) that returns {result}.\n"
    "Compute 17*19 using the tool.\n"
    "Then return JSON with:\n"
    "- final_result\n"
    "- tool_calls: a list of tool call summaries with `tool_name` and `result`\n\n"
    "Return ONLY valid JSON. No markdown."
)


class CalculationStep(BaseModel):
    """Structured tool-step summary."""

    tool_name: str
    result: int


class CalculationAudit(BaseModel):
    """Provider-independent parser for the common calculation result."""

    steps: list[CalculationStep] = Field(min_length=2)
    final_result: int


def _calculation_audit_schema(description: str) -> type[BaseModel]:
    step_schema = create_model(
        "CalculationStep",
        tool_name=(str, ...),
        result=(int, ...),
        __doc__="Structured tool-step summary.",
    )
    return create_model(
        "CalculationAudit",
        steps=(list[step_schema], Field(min_length=2)),
        final_result=(int, ...),
        __doc__=description,
    )


class ProfileToolAudit(BaseModel):
    final_result: int
    tool_calls: list[CalculationStep] = Field(min_length=1)


def _profile_tool_audit_schema() -> type[BaseModel]:
    tool_call_schema = create_model(
        "ToolCallSummary",
        tool_name=(str, ...),
        result=(int, ...),
        __doc__="Structured tool-call summary for the final JSON response.",
    )
    return create_model(
        "CalculationAudit",
        final_result=(int, ...),
        tool_calls=(list[tool_call_schema], Field(min_length=1)),
        __doc__="Structured result for the profile-tools scenario.",
    )


def add(*, a: int, b: int) -> dict[str, int]:
    """Return a+b as JSON."""
    return {"result": a + b}


def multiply(*, a: int, b: int) -> dict[str, int]:
    """Return a*b as JSON."""
    return {"result": a * b}


def _usage_payload(response: LLMRouterResponse) -> object:
    return (
        response.usage.model_dump(mode="json") if response.usage is not None else None
    )


@given(
    parsers.parse('the "{route}" multi-round tool route'),
    target_fixture="multi_round_route",
)
def provider_multi_round_route(
    route: str,
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> tuple[LLMRouter, type[BaseModel]]:
    if route == "QwenChat":
        router = LLMRouter(
            RouterProfile(model=Model.QWEN_MAX_LATEST, provider=Provider.QWENCHAT),
            temperature=0.0,
            seed=42,
        )
        description = "Structured result for the QwenChat tools scenario."
    elif route == "AI Studio":
        router = LLMRouter(
            RouterProfile(model=Model.GEMINI_FLASH_LITE, provider=Provider.AISTUDIO),
            temperature=0.0,
            seed=42,
        )
        description = "Structured result for the AI Studio tools scenario."
    elif route == "Gemini WebAPI":
        prepare_gemini_webapi_runtime(monkeypatch, request)
        router = LLMRouter(
            RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.GEMINI_WEBAPI),
            temperature=0.0,
            seed=42,
        )
        description = "Structured result for the Gemini WebAPI tools scenario."
    else:  # pragma: no cover - Examples owns the valid values.
        raise ValueError(route)
    return router, _calculation_audit_schema(description)


@when("the route executes the calculation workflow:", target_fixture="response")
def execute_calculation_workflow(
    multi_round_route: tuple[LLMRouter, type[BaseModel]],
    docstring: str,
) -> LLMRouterResponse:
    router, response_schema = multi_round_route
    evidence.contract("Response schema", response_schema)
    evidence.contract("Tool · add", add)
    evidence.contract("Tool · multiply", multiply)
    return router.query(
        [_SYSTEM_PROMPT, docstring],
        tools=[add, multiply],
        tool_choice="required",
        response_schema=response_schema,
        max_tool_rounds=4,
    )


@then("the structured workflow reports add and multiply with final result 84")
def multi_round_workflow_is_preserved(response: LLMRouterResponse) -> None:
    audit = CalculationAudit.model_validate(parse_json_object(response.output_text))
    assert audit.final_result == 84
    assert len(audit.steps) >= 2
    assert {step.tool_name for step in audit.steps} >= {"add", "multiply"}
    assert response.tool_trace
    assert "add" in {step.tool_name for step in response.tool_trace}
    evidence.json(
        "Result",
        {
            "provider": str(response.provider),
            "model": str(response.model),
            "usage": _usage_payload(response),
            "tool_trace": [
                step.model_dump(mode="json") for step in response.tool_trace
            ],
            "calculation": audit.model_dump(mode="json"),
        },
    )


@given(
    "the OpenAI-compatible local multi-round route",
    target_fixture="local_multi_round_case",
)
def openai_compatible_local_multi_round_route() -> dict[str, object]:
    return {}


@when("the local route executes add then multiply")
def execute_local_multi_round(
    local_multi_round_case: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY_1", "local-openrouter-key")
    path = openai_chat_path()
    final_payload = json.dumps(
        {
            "steps": [
                {"tool_name": "add", "result": 42},
                {"tool_name": "multiply", "result": 84},
            ],
            "final_result": 84,
        }
    )
    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", path): [
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=openai_tool_call_response(
                        tool_name="add",
                        args={"a": 40, "b": 2},
                    ),
                ),
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=openai_tool_call_response(
                        tool_name="multiply",
                        args={"a": 42, "b": 2},
                    ),
                ),
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=openai_success_response(text=final_payload),
                ),
            ]
        },
    ) as server:
        with patched_openai_sdk(
            forced_base_url=f"{server.base_url}/v1",
            disable_sdk_retries=True,
        ):
            response_schema = _calculation_audit_schema(
                "Structured result for the local OpenAI-compatible tools scenario."
            )
            response = LLMRouter(
                RouterProfile(
                    model=Model.DEEPSEEK_V3,
                    provider=Provider.OPENROUTER,
                ),
                temperature=0.0,
                seed=42,
            ).query(
                [
                    _SYSTEM_PROMPT,
                    "Use add with a=40,b=2, then multiply that result by 2.",
                ],
                tools=[add, multiply],
                tool_choice="required",
                response_schema=response_schema,
                max_tool_rounds=4,
            )
        requests = server.recorded_requests("POST", path)

    local_multi_round_case["response"] = response
    local_multi_round_case["requests"] = requests


@then("the local workflow reports add and multiply with final result 84")
def local_multi_round_is_preserved(
    local_multi_round_case: dict[str, object],
) -> None:
    response = local_multi_round_case["response"]
    assert isinstance(response, LLMRouterResponse)
    audit = CalculationAudit.model_validate(parse_json_object(response.output_text))
    assert audit.final_result == 84
    assert [step.tool_name for step in response.tool_trace] == ["add", "multiply"]

    requests = local_multi_round_case["requests"]
    assert isinstance(requests, list)
    assert len(requests) == 3
    payloads = [json.loads(request.body.decode("utf-8")) for request in requests]
    second_tool_results = [
        message for message in payloads[1]["messages"] if message.get("role") == "tool"
    ]
    third_tool_results = [
        message for message in payloads[2]["messages"] if message.get("role") == "tool"
    ]
    assert len(second_tool_results) == 1
    assert len(third_tool_results) == 2
    assert json.loads(second_tool_results[0]["content"]) == {"result": 42}
    assert json.loads(third_tool_results[-1]["content"]) == {"result": 84}
    evidence.json(
        "Result",
        {
            "provider": str(response.provider),
            "tool_trace": [
                step.model_dump(mode="json") for step in response.tool_trace
            ],
            "round_trip_tool_results": [
                json.loads(message["content"]) for message in third_tool_results
            ],
            "calculation": audit.model_dump(mode="json"),
        },
    )


@given(
    "a Google GenAI route with a profile-level multiply tool", target_fixture="router"
)
def google_profile_tool_route() -> LLMRouter:
    evidence.contract("Profile tool · multiply", multiply)
    return LLMRouter(
        RouterProfile(
            provider=Provider.GOOGLE,
            model=Model.GEMINI_FLASH_LITE,
            tools=[multiply],
        ),
        temperature=0.0,
        seed=42,
    )


@when("the route is required to calculate 17 times 19", target_fixture="response")
def execute_profile_tool_workflow(router: LLMRouter) -> LLMRouterResponse:
    response_schema = _profile_tool_audit_schema()
    evidence.contract("Response schema", response_schema)
    return router.query(
        _PROFILE_TOOL_PROMPT,
        tool_choice="required",
        response_schema=response_schema,
        max_tool_rounds=4,
    )


@then("the structured result and runtime trace report multiply with result 323")
def profile_tool_workflow_is_preserved(response: LLMRouterResponse) -> None:
    audit = ProfileToolAudit.model_validate(parse_json_object(response.output_text))
    assert audit.final_result == 323
    assert audit.tool_calls
    assert audit.tool_calls[0].tool_name == "multiply"
    assert response.tool_trace
    assert len(response.routing_trace) == 1
    assert response.routing_trace[0].provider == Provider.GOOGLE.value
    evidence.json(
        "Result",
        {
            "provider": str(response.provider),
            "model": str(response.model),
            "usage": _usage_payload(response),
            "tool_trace": [
                step.model_dump(mode="json") for step in response.tool_trace
            ],
            "calculation": audit.model_dump(mode="json"),
        },
    )
