# %%
"""Google GenAI remote-video structured-output workbench script.

Why:
    Shows that the native Google client accepts the same remote video URL plus
    metadata shape the adapter builds for `VideoUrlSchema`.

Covers:
    Area: google-genai live remote video input
    Behavior: file URI video reference, video metadata, structured output
    Interface: `Client.models.generate_content(...)`

Checks:
    If the native Google client accepts the fixed public video URL, then the remote-
        video seam is working.
    If the response parses into the requested video observation schema, then the
        structured-output contract is working on the live remote-video response.
    If the parsed result exposes indoor action and location cues, then the output stayed
        grounded in the shared public clip.
    If the result also exposes `video_url` and `usage`, then the manual run keeps the
        exact remote input and token accounting visible beside the parsed video summary.

Examples:
    Run manually:
        uv run python -m workbench.llm_router.google_genai.video_url_structured
        uv run python scripts/runtime/reproduce_running_loop.py \
            workbench.llm_router.google_genai.video_url_structured
"""

from __future__ import annotations

from typing import Any

from google.genai import types

from tests.support.console import console
from workbench.llm_router.google_genai._media_parts import build_video_url_part
from workbench.llm_router.google_genai._sdk_helpers import (
    build_client,
    parsed_response_dict,
    usage_snapshot,
)
from workbench.llm_router.google_genai._structured_output import (
    VideoObservation,
    build_indoor_video_prompt,
)

# =============================================================================
# Scenario
# =============================================================================

# Keep the same preview model and one fixed public video URL so the remote
# file-data request shape is the main thing under inspection.
_MODEL = "gemini-2.5-flash"
_PROMPT = build_indoor_video_prompt()
_VIDEO_URL = "https://www.youtube.com/shorts/QUxqvF0pyGw"


# =============================================================================
# Helpers
# =============================================================================
# No local helpers for this scenario.


# =============================================================================
# Pipeline
# =============================================================================


def run_pipeline() -> dict[str, Any]:
    """Run one real native Google remote-video request."""
    # Build the native client and attach the remote clip using the same
    # file-data plus video-metadata shape the adapter builds.
    client = build_client()
    # Keep the parsed JSON, usage, and URL together so a manual run clearly
    # shows which remote input produced the output.
    response = client.models.generate_content(
        model=_MODEL,
        contents=[_PROMPT, build_video_url_part(_VIDEO_URL)],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=VideoObservation,
            temperature=0,
            seed=42,
        ),
    )
    return {
        "parsed": parsed_response_dict(response),
        "usage": usage_snapshot(response),
        "video_url": _VIDEO_URL,
    }


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the workbench script as a narrative manual demo."""
    console.demo_intro(__doc__)
    console.demo_step(
        "Scenario",
        "Sending one remote video URI through the native Google client with "
        "video metadata.",
        details=(
            f"Model: {_MODEL}",
            f"Video URL: {_VIDEO_URL}",
            "Why this shape: it matches the remote video part the adapter builds.",
        ),
    )

    result = run_pipeline()
    parsed = result["parsed"]
    console.demo_step(
        "Observed Structured Video Output",
        "The live response returned structured action and location data for the "
        "remote clip.",
        details=(
            f"action: {parsed['action']}",
            f"location: {parsed['location']}",
            f"usage: {result['usage']}",
        ),
    )
    console.print_json(result)
    console.demo_outcome(
        "This is enough to trust that the native remote-video URI path works in "
        "this environment.",
    )


if __name__ == "__main__":
    main()


# =============================================================================
# Expected Output
# =============================================================================
EXPECTED_OUTPUT = """
Real run on 2026-04-03 (excerpt, cut after 12 lines):
{
  "parsed": {
    "action": "partner workout",
    "evidence": [
      "one woman squats while supporting another",
      "mirrors and gym equipment in the background"
    ],
    "location": "an indoor gym"
  },
  "usage": {
    "input_tokens": 4213,
    "output_tokens": 36,
""".strip()
