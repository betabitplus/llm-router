"""Call a Python tool
==================

Give the model a normal Python function, require one tool call, and inspect both the
local execution step and the typed final answer.
"""
# sphinx_gallery_tags = ["tools", "structured-output", "routing"]
# sphinx_gallery_thumbnail_path = "_static/gallery/tool-calling.svg"

from __future__ import annotations

from pydantic import BaseModel

from llm_router import LLMRouter, Model, Provider, RouterProfile


# %%
# Define the tool and final shape
# -------------------------------
# A tool is just a typed Python callable. The response schema is independent and
# describes what the model must return after the tool loop finishes.
class CalcResult(BaseModel):
    """Typed final answer returned after the tool loop."""

    result: int


def multiply(*, a: int, b: int) -> dict[str, int]:
    """Multiply two integers."""
    return {"result": a * b}


# %%
# Run the tool loop
# -----------------
# ``tools=[multiply]`` exposes the function; ``tool_choice="required"`` makes the
# model use it. The router executes the function locally and continues the model
# turn with its result.
if __name__ == "__main__":
    router = LLMRouter(
        RouterProfile(model=Model.GEMINI_FLASH_LITE, provider=Provider.AISTUDIO),
        temperature=0.0,
        seed=42,
    )
    response = router.query(
        "Use the tool to compute 17 * 19, then return the result.",
        tools=[multiply],
        tool_choice="required",
        response_schema=CalcResult,
        max_tool_rounds=4,
    )
    result = CalcResult.model_validate_json(response.output_text)
    step = response.tool_trace[0]

    print(f"tool: {step.tool_name}(a={step.args['a']}, b={step.args['b']})")
    print(f"tool result: {step.result['result']}")
    print(f"final result: {result.result}")

# %%
# The matching tool and final values show the complete loop: the model requested the
# function, the router executed it locally, and the model returned a typed answer.
