# %%
"""Bindings for the multi-round tool execution living specification."""

from __future__ import annotations

from py_lib_testkit import evidence
from pydantic import BaseModel, Field
from pytest_bdd import given, scenarios, then, when

from llm_router import LLMRouter, LLMRouterResponse, Model, Provider, RouterProfile
from tests.llm_router.support.assertions import parse_json_object

scenarios("tools/multi_round.feature")

_SYSTEM_PROMPT = "Follow instructions exactly. Reply with only what is asked."
_TEST_MODULE = "tests/llm_router/bdd/tools/test_multi_round.py"


class CalculationStep(BaseModel):
    """Structured tool-step summary."""

    tool_name: str
    result: int


class CalculationAudit(BaseModel):
    """Structured result for the QwenChat tools scenario."""

    steps: list[CalculationStep] = Field(min_length=2)
    final_result: int


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


@given("the QwenChat multi-round tool route", target_fixture="router")
def qwenchat_multi_round_route() -> LLMRouter:
    """Build the QwenChat route used by the multi-round workflow."""
    return LLMRouter(
        RouterProfile(model=Model.QWEN_MAX_LATEST, provider=Provider.QWENCHAT),
        temperature=0.0,
        seed=42,
    )


@when("the route executes the calculation workflow:", target_fixture="response")
def execute_calculation_workflow(
    router: LLMRouter, docstring: str
) -> LLMRouterResponse:
    """Execute the required multi-round tool workflow from the Gherkin request."""
    return router.query(
        [_SYSTEM_PROMPT, docstring],
        tools=[add, multiply],
        tool_choice="required",
        response_schema=CalculationAudit,
        max_tool_rounds=4,
    )


@then("the structured workflow reports add and multiply with final result 84")
def multi_round_workflow_is_preserved(response: LLMRouterResponse) -> None:
    """Validate the final structured workflow and the runtime tool trace."""
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


# %% Run this cell in VS Code's Interactive Window for a real provider call.
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
