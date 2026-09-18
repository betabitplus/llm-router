# %%
"""Bindings for the explicit tool-choice BDD scenario."""

from __future__ import annotations

import json

import pytest
from py_lib_testkit import evidence
from pydantic import BaseModel
from pytest_bdd import given, parsers, scenarios, then, when

from llm_router import LLMRouter, LLMRouterResponse, Model, Provider, RouterProfile
from tests.llm_router.bdd._support import prepare_gemini_webapi_runtime
from tests.llm_router.support.assertions import parse_json_object
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    google_generate_path,
    google_success_response,
)
from tests.llm_router.support.workers.tool_failure import google_tool_call_response
from tests.llm_router.support.workers.worker_patches import patched_google_genai_sdk

scenarios("tools/tool_choice.feature")

for _test_name, _criterion in (
    (
        "test_a_provider_route_honors_an_explicit_add_tool_choice",
        "VC_TOOL_CHOICE_REPLAY_FAMILIES",
    ),
    (
        "test_ai_studio_honors_an_explicit_add_tool_choice",
        "VC_TOOL_CHOICE_REPLAY_FAMILIES",
    ),
    (
        "test_google_genai_honors_an_explicit_add_tool_choice",
        "VC_TOOL_CHOICE_GOOGLE_GENAI",
    ),
):
    globals()[_test_name] = pytest.mark.coverage_item(_criterion)(globals()[_test_name])
del _criterion, _test_name

_SYSTEM_PROMPT = "Follow instructions exactly. Reply with only what is asked."


class ToolResult(BaseModel):
    """Structured result for the forced-tool-choice scenario."""

    tool_name: str
    final_result: int
    explanation: str


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


@given(parsers.parse('the "{route}" tool-choice route'), target_fixture="router")
def provider_tool_choice_route(
    route: str,
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> LLMRouter:
    if route == "QwenChat":
        return LLMRouter(
            RouterProfile(model=Model.QWEN_MAX_LATEST, provider=Provider.QWENCHAT),
            temperature=0.0,
            seed=42,
        )
    if route == "OpenAI-compatible":
        return LLMRouter(
            RouterProfile(model=Model.LLAMA_8B, provider=Provider.NVIDIA),
            temperature=0.0,
            seed=42,
        )
    if route == "Gemini WebAPI":
        prepare_gemini_webapi_runtime(monkeypatch, request)
        return LLMRouter(
            RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.GEMINI_WEBAPI),
            temperature=0.0,
            seed=42,
        )
    raise ValueError(route)  # pragma: no cover - Examples owns the valid values.


@when("the route is forced to use add:", target_fixture="response")
def force_add_tool(router: LLMRouter, docstring: str) -> LLMRouterResponse:
    evidence.contract("Response schema", ToolResult)
    evidence.contract("Tool · add", add)
    evidence.contract("Tool · multiply", multiply)
    return router.query(
        [_SYSTEM_PROMPT, docstring],
        tools=[add, multiply],
        tool_choice={"type": "function", "function": {"name": "add"}},
        response_schema=ToolResult,
        max_tool_rounds=2,
    )


@then("the structured result and runtime trace show only add with result 42")
def forced_tool_choice_is_preserved(response: LLMRouterResponse) -> None:
    result = ToolResult.model_validate(parse_json_object(response.output_text))
    assert result.tool_name == "add"
    assert result.final_result == 42
    assert result.explanation.strip()
    assert response.tool_trace
    assert {step.tool_name for step in response.tool_trace} == {"add"}
    evidence.json(
        "Result",
        {
            "provider": str(response.provider),
            "model": str(response.model),
            "usage": _usage_payload(response),
            "tool_trace": [
                step.model_dump(mode="json") for step in response.tool_trace
            ],
            "tool_result": result.model_dump(mode="json"),
        },
    )


@given("the AI Studio numeric tool-choice route", target_fixture="router")
def aistudio_numeric_tool_choice_route() -> LLMRouter:
    return LLMRouter(
        RouterProfile(model=Model.GEMINI_FLASH_LITE, provider=Provider.AISTUDIO),
        temperature=0.0,
        seed=42,
    )


@when("the route is forced to add 40 and 2", target_fixture="response")
def force_aistudio_add(router: LLMRouter) -> LLMRouterResponse:
    evidence.contract("Tool · add", add)
    evidence.contract("Tool · multiply", multiply)
    prompt = (
        "You have tools add(a, b) and multiply(a, b), each returning {result}.\n"
        "Use ONLY add with a=40 and b=2, then reply with ONLY the number."
    )
    return router.query(
        [_SYSTEM_PROMPT, prompt],
        tools=[add, multiply],
        tool_choice={"type": "function", "function": {"name": "add"}},
        max_tool_rounds=2,
    )


@then("the reply is 42 and the runtime trace shows only add")
def aistudio_add_choice_is_preserved(response: LLMRouterResponse) -> None:
    assert response.output_text.strip().rstrip(".") == "42"
    assert response.tool_trace
    assert {step.tool_name for step in response.tool_trace} == {"add"}
    evidence.json(
        "Result",
        {
            "provider": str(response.provider),
            "model": str(response.model),
            "usage": _usage_payload(response),
            "tool_trace": [
                step.model_dump(mode="json") for step in response.tool_trace
            ],
            "reply": response.output_text,
        },
    )


@given("the Google GenAI local tool-choice route", target_fixture="google_case")
def google_genai_local_tool_choice_route() -> dict[str, object]:
    return {}


@when("the Google route is forced to use add")
def force_google_add(
    google_case: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GOOGLE_API_KEY_1", "local-google-key")
    path = google_generate_path(model=Model.GEMINI_FLASH)
    final_payload = json.dumps(
        {
            "tool_name": "add",
            "final_result": 42,
            "explanation": "The explicitly selected add tool returned 42.",
        }
    )
    with ScriptedHTTPServer(
        port=0,
        routes={
            ("POST", path): [
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=google_tool_call_response(
                        tool_name="add",
                        args={"a": 40, "b": 2},
                    ),
                ),
                ScriptedResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=google_success_response(text=final_payload),
                ),
            ]
        },
    ) as server:
        with patched_google_genai_sdk(server_base_url=server.base_url):
            response = LLMRouter(
                RouterProfile(
                    model=Model.GEMINI_FLASH,
                    provider=Provider.GOOGLE,
                ),
                temperature=0.0,
                seed=42,
            ).query(
                [_SYSTEM_PROMPT, "Use add with a=40 and b=2, then return the result."],
                tools=[add, multiply],
                tool_choice={"type": "function", "function": {"name": "add"}},
                response_schema=ToolResult,
                max_tool_rounds=2,
            )
        requests = server.recorded_requests("POST", path)

    google_case["response"] = response
    google_case["requests"] = requests


@then("the Google request and runtime trace show only add with result 42")
def google_add_choice_is_preserved(google_case: dict[str, object]) -> None:
    response = google_case["response"]
    assert isinstance(response, LLMRouterResponse)
    result = ToolResult.model_validate(parse_json_object(response.output_text))
    assert result.tool_name == "add"
    assert result.final_result == 42
    assert response.tool_trace
    assert {step.tool_name for step in response.tool_trace} == {"add"}

    requests = google_case["requests"]
    assert isinstance(requests, list)
    assert len(requests) == 2
    first_payload = json.loads(requests[0].body.decode("utf-8"))
    calling = first_payload["toolConfig"]["functionCallingConfig"]
    assert calling["mode"] == "ANY"
    assert calling["allowedFunctionNames"] == ["add"]
    evidence.json(
        "Result",
        {
            "provider": str(response.provider),
            "model": str(response.model),
            "tool_trace": [
                step.model_dump(mode="json") for step in response.tool_trace
            ],
            "provider_tool_config": calling,
            "tool_result": result.model_dump(mode="json"),
        },
    )
