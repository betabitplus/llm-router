# %%
"""Gemini WebAPI async text-generation workbench script.

Why:
    Shows that `gemini-webapi` can run one explicitly async
    browser-authenticated text request.

Covers:
    Area: gemini-webapi live async text generation
    Behavior: async session init, prompt execution, plain-text output
    Interface: `GeminiClient.init()` and `await GeminiClient.generate_content()`

Checks:
    If the browser-authenticated async session initializes successfully from local
        cookies, then the local runtime can reach a real Gemini WebAPI session.
    If one live plain-text prompt returns assistant `text`, then the manual run proves
        the authenticated async text path is working end to end.

Examples:
    Run manually:
        uv run python -m workbench.llm_router.gemini_webapi.text_generation_async
        uv run python scripts/runtime/reproduce_running_loop.py \
            workbench.llm_router.gemini_webapi.text_generation_async
"""

from __future__ import annotations

from typing import Any

from py_lib_tooling import console, run_async

from workbench.llm_router.gemini_webapi._opera_cookie_client import managed_client

# =============================================================================
# Scenario
# =============================================================================

# Keep the prompt tiny so the script isolates explicit async session startup
# and response flow, not prompt creativity.
_MODEL = "gemini-3.0-flash"
_PROMPT = "Reply with only OK."


# =============================================================================
# Helpers
# =============================================================================
# No local helpers for this scenario.


# =============================================================================
# Pipeline
# =============================================================================


async def run_pipeline() -> dict[str, Any]:
    """Run the real async Gemini WebAPI text-generation flow."""
    # Build, initialize, and close one browser-authenticated client through a
    # single managed helper so the script stays focused on the async text seam.
    async with managed_client(init_timeout_seconds=30.0) as client:
        output = await client.generate_content(_PROMPT, model=_MODEL)
        return {
            "model": _MODEL,
            "text": output.text.strip(),
        }


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the workbench script as a narrative manual demo."""
    console.demo_intro(__doc__)
    console.demo_step(
        "Scenario",
        "Starting one real Gemini WebAPI session from local Opera cookies and "
        "sending a very short text prompt through the explicit async path.",
        details=(
            f"Model: {_MODEL}",
            f"Prompt: {_PROMPT}",
            "Why this prompt: any short reply is enough to prove the live "
            "async session worked.",
        ),
    )

    result = run_async(run_pipeline())
    console.demo_step(
        "Observed Async Text Output",
        "The live web-session-backed client returned plain text from the async prompt.",
        details=(
            f"text: {result['text']}",
            "This is the visible consequence of successful async session init "
            "and prompt execution.",
        ),
    )
    console.print_json(result)
    console.demo_outcome(
        "A real async browser-authenticated Gemini WebAPI session is working "
        "in this environment.",
    )


if __name__ == "__main__":
    main()


# =============================================================================
# Expected Output
# =============================================================================
EXPECTED_OUTPUT = """
Real run on 2026-04-03:
{
  "model": "gemini-3.0-flash",
  "text": "OK"
}
""".strip()
