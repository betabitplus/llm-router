# %%
"""AI Studio async text-generation workbench script.

Why:
    Shows that AI Studio can return plain text through the async
    OpenAI-compatible endpoint before any structured-output or tool-specific
    behavior is involved.

Covers:
    Area: AI Studio non-video path
    Behavior: async text input, plain-text output
    Interface: `AsyncOpenAI().chat.completions.create(...)`

Checks:
    If one live async plain-text request succeeds through the AI Studio non-video path,
        then the OpenAI-compatible text route accepts the configured prompt.
    If the response exposes assistant `text`, then the manual run proves the provider
        returned usable completion content.
    If the response exposes `usage`, then the manual run also proves token accounting
        survived the live request.

Examples:
    Run manually:
        uv run python -m workbench.llm_router.aistudio.text_generation_async
        uv run python scripts/runtime/reproduce_running_loop.py \
            workbench.llm_router.aistudio.text_generation_async
"""

from __future__ import annotations

from typing import Any

from py_lib_tooling import console, run_async

from workbench.llm_router.aistudio._sdk_helpers import (
    build_async_client,
    response_text,
    usage_snapshot,
)

# =============================================================================
# Scenario
# =============================================================================

# Keep the baseline flash model fixed so this script stays about the plain
# async non-video AI Studio path rather than schema or tool quirks.
_MODEL = "gemini-2.5-flash"
_PROMPT = "Reply with only OK."


# =============================================================================
# Helpers
# =============================================================================
# No local helpers for this scenario.


# =============================================================================
# Pipeline
# =============================================================================


async def run_pipeline() -> dict[str, Any]:
    """Run one real async AI Studio text-generation request."""
    client = build_async_client()
    response = await client.chat.completions.create(
        model=_MODEL,
        messages=[{"role": "user", "content": _PROMPT}],
        temperature=0.0,
    )
    return {
        "model": _MODEL,
        "text": response_text(response),
        "usage": usage_snapshot(response),
    }


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


async def main() -> None:
    """Run the workbench script as a narrative manual demo."""
    console.demo_intro(__doc__)
    console.demo_step(
        "Scenario",
        "Sending one tiny plain-text prompt through the async AI Studio "
        "OpenAI-compatible endpoint.",
        details=(
            f"Model: {_MODEL}",
            f"Prompt: {_PROMPT}",
        ),
    )

    result = await run_pipeline()
    console.demo_step(
        "Observed Text Output",
        "The live non-video AI Studio async path returned a short plain-text answer.",
        details=(
            f"text: {result['text']}",
            f"usage: {result['usage']}",
        ),
    )
    console.print_json(result)
    console.demo_outcome(
        "This is enough to trust that the basic async AI Studio text path works "
        "in this environment.",
    )


if __name__ == "__main__":
    run_async(main())


# =============================================================================
# Expected Output
# =============================================================================
EXPECTED_OUTPUT = """
Real run on 2026-04-03:
{
  "model": "gemini-2.5-flash",
  "text": "OK",
  "usage": {
    "input_tokens": 6,
    "output_tokens": 1,
    "total_tokens": 37
  }
}
""".strip()
