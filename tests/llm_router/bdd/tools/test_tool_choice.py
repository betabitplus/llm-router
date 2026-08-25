# %%
"""Bindings for the explicit tool-choice living specification."""

from __future__ import annotations

from py_lib_testkit import evidence
from pydantic import BaseModel
from pytest_bdd import given, parsers, scenarios, then, when

from llm_router import LLMRouter, LLMRouterResponse, Model, Provider, RouterProfile
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
def provider_tool_choice_route(route: str) -> LLMRouter:
    """Build the provider route named by the specification example."""
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
    raise ValueError(route)  # pragma: no cover - Examples owns the valid values.


@when("the route is forced to use add:", target_fixture="response")
def force_add_tool(router: LLMRouter, docstring: str) -> LLMRouterResponse:
    """Execute the named-tool workflow using the Gherkin request."""
    return router.query(
        [_SYSTEM_PROMPT, docstring],
        tools=[add, multiply],
        tool_choice={"type": "function", "function": {"name": "add"}},
        response_schema=ToolResult,
        max_tool_rounds=2,
    )


@then("the structured result and runtime trace show only add with result 42")
def forced_tool_choice_is_preserved(response: LLMRouterResponse) -> None:
    """Validate that both the final result and runtime trace honor the forced tool."""
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


# %% QwenChat live: run this cell in VS Code's Interactive Window.
if __name__ == "__main__":
    import ipytest

    ipytest.run(
        "-q",
        "-s",
        "--disable-recording",
        "--no-cov",
        "-k",
        "QwenChat",
        _TEST_MODULE,
        defopts=False,
        raise_on_error=True,
    )
# %% OpenAI-compatible live: run this cell separately when desired.
if __name__ == "__main__":
    import ipytest

    ipytest.run(
        "-q",
        "-s",
        "--disable-recording",
        "--no-cov",
        "-k",
        "OpenAI-compatible",
        _TEST_MODULE,
        defopts=False,
        raise_on_error=True,
    )
# %%
