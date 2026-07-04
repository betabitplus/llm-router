# %%
"""Google GenAI local-video structured-output workbench script.

Why:
    Shows that the native Google client accepts the same inline video blob plus
    metadata shape the adapter builds for `VideoSchema`.

Covers:
    Area: google-genai live local video input
    Behavior: inline video blob, video metadata, structured output
    Interface: `Client.models.generate_content(...)`

Checks:
    If the native Google client accepts the shared MP4 fixture, then the local video-
        input seam is working.
    If the response parses into the requested video observation schema, then the
        structured-output contract is working on the live video response.
    If the parsed result exposes jump or leap action plus rooftop or tall-building
        location cues, then the output stayed grounded in the shared clip.
    If the result also exposes `usage`, then the manual run keeps token accounting
        beside the parsed video summary.

Examples:
    Run manually:
        uv run python -m workbench.llm_router.google_genai.video_file_structured
        uv run python scripts/runtime/reproduce_running_loop.py \
            workbench.llm_router.google_genai.video_file_structured
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from google.genai import types

from tests.support.console import console
from workbench.llm_router.google_genai._media_parts import build_video_file_part
from workbench.llm_router.google_genai._sdk_helpers import (
    build_client,
    parsed_response_dict,
    usage_snapshot,
)
from workbench.llm_router.google_genai._structured_output import (
    VideoObservation,
    build_rooftop_video_prompt,
)

# =============================================================================
# Scenario
# =============================================================================

# Keep the shared jumper clip fixed so the manual result is about the inline
# video-plus-metadata request shape, not a changing fixture.
_MODEL = "gemini-2.5-flash"
_REPO_ROOT = Path(__file__).resolve().parents[3]
_VIDEO_PATH = _REPO_ROOT / "tests/llm_router/data/jumper.mp4"
_PROMPT = build_rooftop_video_prompt()


# =============================================================================
# Helpers
# =============================================================================
# No local helpers for this scenario.


# =============================================================================
# Pipeline
# =============================================================================


def run_pipeline() -> dict[str, Any]:
    """Run one real native Google local-video request."""
    # Build the native client and send the MP4 using the same inline blob plus
    # video metadata shape the adapter builds.
    client = build_client()
    # Keep the parsed JSON and usage snapshot as the manual evidence for the
    # local-video seam.
    response = client.models.generate_content(
        model=_MODEL,
        contents=[_PROMPT, build_video_file_part(_VIDEO_PATH)],
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
    }


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the workbench script as a narrative manual demo."""
    console.demo_intro(__doc__)
    console.demo_step(
        "Scenario",
        "Uploading the shared rooftop-jump clip as an inline video blob with "
        "video metadata.",
        details=(
            f"Model: {_MODEL}",
            f"Video: {_VIDEO_PATH.name}",
            "Why this shape: it matches the local video part the adapter builds.",
        ),
    )

    result = run_pipeline()
    parsed = result["parsed"]
    console.demo_step(
        "Observed Structured Video Output",
        "The live response returned structured action and location data for the clip.",
        details=(
            f"action: {parsed['action']}",
            f"location: {parsed['location']}",
            f"usage: {result['usage']}",
        ),
    )
    console.print_json(result)
    console.demo_outcome(
        "This is enough to trust that the native local-video path works in "
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
    "action": "jumping",
    "evidence": [
      "person in mid-air",
      "city skyline below"
    ],
    "location": "on a skyscraper rooftop"
  },
  "usage": {
    "input_tokens": 2159,
    "output_tokens": 30,
""".strip()
