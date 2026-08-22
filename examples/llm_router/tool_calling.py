"""Tool calling with structured output
===================================

Let a real model call a local Python tool and return the final answer through a
typed response schema.
"""
# sphinx_gallery_tags = ["tools", "structured-output", "routing"]
# sphinx_gallery_thumbnail_path = "_static/gallery/tool-calling.svg"
# %%

from __future__ import annotations

from pydantic import BaseModel

from llm_router import LLMRouter, Model, Provider, RouterProfile


class CalcResult(BaseModel):
    """Final typed result."""

    result: int


def multiply(*, a: int, b: int) -> dict[str, int]:
    """Multiply two integers."""
    return {"result": a * b}


def main() -> None:
    """Run the live tool loop."""
    router = LLMRouter(
        RouterProfile(model=Model.GEMINI_FLASH_LITE, provider=Provider.GOOGLE),
        temperature=0.0,
        seed=42,
    )
    response = router.query(
        (
            "Compute 17*19 using the tool, then return ONLY valid JSON with the "
            "result field. No markdown or code fences."
        ),
        tools=[multiply],
        tool_choice="required",
        response_schema=CalcResult,
        max_tool_rounds=4,
    )
    parsed = CalcResult.model_validate_json(response.output_text)
    print(parsed.model_dump_json(indent=2))
    print(f"tool_trace={response.tool_trace}")


# %%
if __name__ == "__main__":
    main()
