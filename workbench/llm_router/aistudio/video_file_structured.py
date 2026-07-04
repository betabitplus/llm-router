# %%
"""AI Studio local-video structured-output workbench script.

Why:
    Shows that AI Studio switches to the native streamed Gemini-style endpoint
    for local video input and still returns structured JSON.

Covers:
    Area: AI Studio native video path
    Behavior: local video upload, Gemini-native payload, structured output
    Interface: `/v1beta/models/...:streamGenerateContent`

Checks:
    If the native AI Studio video path accepts the shared MP4 fixture, then the local
        video-input seam is working.
    If the response parses into the requested video observation schema, then the
        structured-output contract is working on the live video response.
    If the parsed result exposes jump or leap action plus rooftop or tall-building
        location cues, then the output stayed grounded in the shared clip.
    If the result also exposes `endpoint` and `usage`, then the manual run keeps the
        native route and token accounting visible beside the parsed video summary.

Examples:
    Run manually:
        uv run python -m workbench.llm_router.aistudio.video_file_structured
        uv run python scripts/runtime/reproduce_running_loop.py \
            workbench.llm_router.aistudio.video_file_structured
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tests.support.console import console
from workbench.llm_router.aistudio._native_media import (
    build_local_video_part,
    build_text_part,
    run_sync_native_request,
)
from workbench.llm_router.aistudio._structured_output import (
    VideoObservation,
    build_rooftop_video_prompt,
)

# =============================================================================
# Scenario
# =============================================================================

_REPO_ROOT = Path(__file__).resolve().parents[3]
# Keep the shared jumper clip fixed so this script stays about the native AI
# Studio video path rather than changing media content.
_MODEL = "gemini-2.5-flash"
_VIDEO_PATH = _REPO_ROOT / "tests/llm_router/data/jumper.mp4"
_SYSTEM_PROMPT = "Follow instructions exactly. Reply with only what is asked."
_PROMPT = build_rooftop_video_prompt()


# =============================================================================
# Helpers
# =============================================================================
# No local helpers for this scenario.


# =============================================================================
# Pipeline
# =============================================================================


def run_pipeline() -> dict[str, Any]:
    """Run one real AI Studio native local-video request."""
    # Call the native streamed video helper directly because AI Studio video
    # does not use the OpenAI-compatible path.
    result = run_sync_native_request(
        model=_MODEL,
        parts=[
            build_text_part(_SYSTEM_PROMPT),
            build_text_part(_PROMPT),
            build_local_video_part(path=_VIDEO_PATH, fps=1),
        ],
        response_schema=VideoObservation,
        temperature=0.0,
    )
    parsed = VideoObservation.model_validate(result["parsed"])
    return {
        "endpoint": result["endpoint"],
        "parsed": parsed.model_dump(mode="json"),
        "usage": result["usage"],
    }


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the workbench script as a narrative manual demo."""
    console.demo_intro(__doc__)
    console.demo_step(
        "Scenario",
        "Uploading one local video clip through the native AI Studio streamed "
        "video endpoint.",
        details=(
            f"Model: {_MODEL}",
            f"Video: {_VIDEO_PATH.name}",
            "Why this matters: video does not use the OpenAI-compatible path.",
        ),
    )

    result = run_pipeline()
    parsed = result["parsed"]
    console.demo_step(
        "Observed Native Video Output",
        "The native AI Studio video endpoint returned valid structured JSON for "
        "the local clip.",
        details=(
            f"action: {parsed['action']}",
            f"location: {parsed['location']}",
            f"endpoint: {result['endpoint']}",
        ),
    )
    console.print_json(result)
    console.demo_outcome(
        "This is enough to trust the native AI Studio local-video path in this "
        "environment.",
    )


if __name__ == "__main__":
    main()


# =============================================================================
# Expected Output
# =============================================================================
EXPECTED_OUTPUT = """
Real run on 2026-04-03 (excerpt, cut after 12 lines):
{
  "endpoint": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:streamGenerateContent",
  "parsed": {
    "action": "jumping",
    "evidence": [
      "person in mid-air",
      "jumping between structures"
    ],
    "location": "on a tall building rooftop"
  },
  "usage": {
    "input_tokens": 2169,
""".strip()
