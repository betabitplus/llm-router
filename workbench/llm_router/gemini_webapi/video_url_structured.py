# %%
"""Gemini WebAPI remote-video structured-output workbench script.

Why:
    Shows that `gemini-webapi` can analyze a public video URL when the URL is
    provided directly in the prompt and return structured JSON.

Covers:
    Area: gemini-webapi live remote video input
    Behavior: public video URL in prompt, prompt-driven structured output
    Interface: `GeminiClient.generate_content(...)`

Checks:
    If the browser-authenticated session accepts the fixed public video URL, then the
        remote-video seam is working.
    If the response parses into the requested video observation schema, then the
        structured-output contract is working on the live remote-video response.
    If the parsed result exposes indoor action and location cues, then the output stayed
        grounded in the shared public clip.

Examples:
    Run manually:
        uv run python -m workbench.llm_router.gemini_webapi.video_url_structured
        uv run python scripts/runtime/reproduce_running_loop.py \
            workbench.llm_router.gemini_webapi.video_url_structured
"""

from __future__ import annotations

from typing import Any

from tests.support.console import console
from tests.support.setup import run_async
from workbench.llm_router.gemini_webapi._opera_cookie_client import managed_client
from workbench.llm_router.gemini_webapi._structured_output import (
    VideoObservation,
    build_indoor_video_prompt,
    parse_model_output_json,
)

# =============================================================================
# Scenario
# =============================================================================

# Keep one fixed public clip URL so this script stays about URL-grounded remote
# video analysis rather than changing input sources.
_MODEL = "gemini-3.0-flash"
_VIDEO_URL = "https://www.youtube.com/shorts/QUxqvF0pyGw"
_PROMPT = (
    f"{build_indoor_video_prompt()}\n\nPublic video URL:\n{_VIDEO_URL}\n\n"
    "Analyze the video available at that URL."
)
_INIT_TIMEOUT_SECONDS = 120.0


# =============================================================================
# Helpers
# =============================================================================
# No local helpers for this scenario.


# =============================================================================
# Pipeline
# =============================================================================


async def run_pipeline() -> dict[str, Any]:
    """Run the real live Gemini WebAPI remote-video URL flow."""
    async with managed_client(init_timeout_seconds=_INIT_TIMEOUT_SECONDS) as client:
        output = await client.generate_content(_PROMPT, model=_MODEL)
        parsed = VideoObservation.model_validate(parse_model_output_json(output.text))
        return parsed.model_dump(mode="json")


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the workbench script as a narrative manual demo."""
    console.demo_intro(__doc__)
    console.demo_step(
        "Scenario",
        "Passing one public video URL directly in the Gemini WebAPI prompt and "
        "asking for a structured JSON summary.",
        details=(
            f"Model: {_MODEL}",
            f"Video URL: {_VIDEO_URL}",
            "Why this matters: the web client does not accept remote video URLs "
            "as uploaded files, so the URL must stay in prompt text.",
        ),
    )

    result = run_async(run_pipeline())
    console.demo_step(
        "Observed Structured Video Output",
        "The live session returned JSON describing the public clip's main "
        "action and location.",
        details=(
            f"action: {result['action']}",
            f"location: {result['location']}",
        ),
    )
    console.print_json(result)
    console.demo_outcome(
        "Gemini WebAPI can handle public video URLs through prompt-grounded "
        "structured output in this environment.",
    )


if __name__ == "__main__":
    main()


# =============================================================================
# Expected Output
# =============================================================================
EXPECTED_OUTPUT = """
Real run on 2026-04-03 (excerpt, cut after 12 lines):
{
  "action": "partner workout",
  "evidence": [
    "woman performing partner lift",
    "gym interior with mirrors"
  ],
  "location": "indoors in a gym"
}
""".strip()
