# %%
"""Google GenAI async text-generation workbench script.

Why:
    Shows that the native `google-genai` async client can run one plain text
    request with the same config knobs the adapter injects for ordinary async
    text calls.

Covers:
    Area: google-genai live async text generation
    Behavior: async generation, temperature and seed config
    Interface: `Client.aio.models.generate_content(...)`

Checks:
    If one live async plain-text request succeeds through the native Google client, then
        the async text path accepts the configured prompt.
    If the response exposes assistant `text`, then the manual run proves the SDK
        returned usable completion content.
    If the response exposes `usage`, then the manual run also proves token accounting
        survived the live request.

Examples:
    Run manually:
        uv run python -m workbench.llm_router.google_genai.text_generation_async
        uv run python scripts/runtime/reproduce_running_loop.py \
            workbench.llm_router.google_genai.text_generation_async
"""

from __future__ import annotations

from typing import Any

from google.genai import types
from py_lib_tooling import console, run_async

from workbench.llm_router.google_genai._sdk_helpers import (
    build_client,
    response_text,
    usage_snapshot,
)

# =============================================================================
# Scenario
# =============================================================================

# Keep the same flash model as the sync probe so this script isolates async
# execution rather than model differences.
_MODEL = "gemini-2.5-flash"
_PROMPT = "Reply with only OK."
_TEMPERATURE = 0.0
_SEED = 42


# =============================================================================
# Helpers
# =============================================================================
# No local helpers for this scenario.


# =============================================================================
# Pipeline
# =============================================================================


async def run_pipeline() -> dict[str, Any]:
    """Run one real native Google async text-generation request."""
    # Build the native client once and use its async surface directly.
    client = build_client()
    # Run one live request, then keep only the text and usage evidence needed
    # for manual inspection of the async seam.
    response = await client.aio.models.generate_content(
        model=_MODEL,
        contents=[_PROMPT],
        config=types.GenerateContentConfig(
            temperature=_TEMPERATURE,
            seed=_SEED,
        ),
    )
    return {
        "model": _MODEL,
        "text": response_text(response),
        "usage": usage_snapshot(response),
    }


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the workbench script as a narrative manual demo."""
    console.demo_intro(__doc__)
    console.demo_step(
        "Scenario",
        "Sending one plain text prompt through the native Google async client.",
        details=(
            f"Model: {_MODEL}",
            f"Prompt: {_PROMPT}",
            f"Temperature: {_TEMPERATURE}",
            f"Seed: {_SEED}",
        ),
    )

    result = run_async(run_pipeline())
    console.demo_step(
        "Observed Async Text Output",
        "The native Google async client returned plain text and usage metadata.",
        details=(
            f"text: {result['text']}",
            f"usage: {result['usage']}",
        ),
    )
    console.print_json(result)
    console.demo_outcome(
        "This is enough to trust that the native async text path is working in "
        "this environment.",
    )


if __name__ == "__main__":
    main()


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
    "total_tokens": 41
  }
}
""".strip()
