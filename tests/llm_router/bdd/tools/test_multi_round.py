# %%
"""Bindings for the multi-round tool execution BDD scenario."""

from __future__ import annotations

import pytest
from py_lib_testkit import evidence
from pydantic import BaseModel, Field, create_model
from pytest_bdd import given, parsers, scenarios, then, when

from llm_router import LLMRouter, LLMRouterResponse, Model, Provider, RouterProfile
from tests.llm_router.bdd._support import prepare_gemini_webapi_runtime
from tests.llm_router.support.assertions import parse_json_object

scenarios("tools/multi_round.feature")

_SYSTEM_PROMPT = "Follow instructions exactly. Reply with only what is asked."
_TEST_MODULE = "tests/llm_router/bdd/tools/test_multi_round.py"
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
    "a Google GenAI route with a profile-level multiply tool", target_fixture="router"
)
def google_profile_tool_route() -> LLMRouter:
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
    return router.query(
        _PROFILE_TOOL_PROMPT,
        tool_choice="required",
        response_schema=_profile_tool_audit_schema(),
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


# %% Run this cell for multi-round tool scenarios against live providers.
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
