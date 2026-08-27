# %%
"""Bindings for the explicit tool-choice BDD scenario."""

from __future__ import annotations

import pytest
from py_lib_testkit import evidence
from pydantic import BaseModel
from pytest_bdd import given, parsers, scenarios, then, when

from llm_router import LLMRouter, LLMRouterResponse, Model, Provider, RouterProfile
from tests.llm_router.bdd._support import prepare_gemini_webapi_runtime
from tests.llm_router.support.assertions import parse_json_object

scenarios("tools/tool_choice.feature")

_SYSTEM_PROMPT = "Follow instructions exactly. Reply with only what is asked."
_TEST_MODULE = "tests/llm_router/bdd/tools/test_tool_choice.py"


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


# %% Run this cell for tool-choice scenarios against live providers.
if __name__ == "__main__":
    import ipytest

    ipytest.run(
        "-q",
        "-s",
        "--disable-recording",
        "--no-cov",
        _TEST_MODULE,
        defopts=False,
        raise_on_error=True,
    )
# %%
