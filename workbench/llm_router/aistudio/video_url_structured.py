# %%
"""AI Studio remote-video structured-output workbench script.

Why:
    Shows that AI Studio can analyze a remote video URL through the native
    streamed Gemini-style endpoint and return structured JSON.

Covers:
    Area: AI Studio native video path
    Behavior: remote video URL, Gemini-native payload, structured output
    Interface: `/v1beta/models/...:streamGenerateContent`

Checks:
    If the native AI Studio video path accepts the fixed public video URL, then the
        remote-video seam is working.
    If the response parses into the requested video observation schema, then the
        structured-output contract is working on the live remote-video response.
    If the parsed result exposes indoor action and location cues, then the output stayed
        grounded in the shared public clip.
    If the result also exposes `endpoint` and `usage`, then the manual run keeps the
        native route and token accounting visible beside the parsed video summary.

Examples:
    Run manually:
        uv run python -m workbench.llm_router.aistudio.video_url_structured
        uv run python scripts/runtime/reproduce_running_loop.py \
            workbench.llm_router.aistudio.video_url_structured
"""

from __future__ import annotations

from typing import Any

from py_lib_tooling import console

from workbench.llm_router.aistudio._native_media import (
    build_remote_video_part,
    build_text_part,
    run_sync_native_request,
)
from workbench.llm_router.aistudio._structured_output import (
    VideoObservation,
    build_indoor_video_prompt,
)

# =============================================================================
# Scenario
# =============================================================================

# Keep one fixed public clip URL so this script stays about the native remote
# video part shape instead of a changing input source.
_MODEL = "gemini-2.5-flash"
_VIDEO_URL = "https://www.youtube.com/shorts/QUxqvF0pyGw"
_SYSTEM_PROMPT = "Follow instructions exactly. Reply with only what is asked."
_PROMPT = build_indoor_video_prompt()


# =============================================================================
# Helpers
# =============================================================================
# No local helpers for this scenario.


# =============================================================================
# Pipeline
# =============================================================================


def run_pipeline() -> dict[str, Any]:
    """Run one real AI Studio native remote-video request."""
    # Call the native streamed video helper directly because remote video URLs
    # also bypass the OpenAI-compatible AI Studio path.
    result = run_sync_native_request(
        model=_MODEL,
        parts=[
            build_text_part(_SYSTEM_PROMPT),
            build_text_part(_PROMPT),
            build_remote_video_part(url=_VIDEO_URL, fps=1),
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
        "Sending one remote video URL through the native AI Studio streamed "
        "video endpoint.",
        details=(
            f"Model: {_MODEL}",
            f"Video URL: {_VIDEO_URL}",
            "Why this matters: remote video URLs use the same native path as "
            "local video files, but a different part shape.",
        ),
    )

    result = run_pipeline()
    parsed = result["parsed"]
    console.demo_step(
        "Observed Native Video Output",
        "The native AI Studio video endpoint returned valid structured JSON for "
        "the remote clip.",
        details=(
            f"action: {parsed['action']}",
            f"location: {parsed['location']}",
            f"endpoint: {result['endpoint']}",
        ),
    )
    console.print_json(result)
    console.demo_outcome(
        "This is enough to trust the native AI Studio remote-video path in this "
        "environment.",
    )


if __name__ == "__main__":
    main()


# =============================================================================
# Expected Output
# =============================================================================
EXPECTED_OUTPUT = """
Real run on 2026-04-04 (excerpt, key verification fields):
{
  "endpoint": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:streamGenerateContent",
  "parsed": {
    "action": "partner exercise",
    "evidence": [
      "one woman squats while supporting another horizontally",
      "mirrored walls and gym equipment in background"
    ],
    "location": "gym and dance studio"
  },
  "usage": {
    "input_tokens": 4223,
    "output_tokens": 38,
    "total_tokens": 4950
  }
}
""".strip()
