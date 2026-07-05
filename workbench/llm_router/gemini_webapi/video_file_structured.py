# %%
"""Gemini WebAPI video structured-output workbench script.

Why:
    Shows that `gemini-webapi` can upload one real local video file and return
    a structured summary of the clip in a live browser-authenticated session.

Covers:
    Area: gemini-webapi live video input
    Behavior: local video upload, prompt-driven structured output
    Interface: `GeminiClient.generate_content(..., files=[...])`

Checks:
    If the browser-authenticated session accepts the shared MP4 fixture, then the local
        video-input seam is working.
    If the response parses into the requested video observation schema, then the
        structured-output contract is working on the live video response.
    If the parsed result exposes jump or leap action plus rooftop or tall-building
        location cues, then the output stayed grounded in the shared clip.

Examples:
    Run manually:
        uv run python -m workbench.llm_router.gemini_webapi.video_file_structured
        uv run python scripts/runtime/reproduce_running_loop.py \
            workbench.llm_router.gemini_webapi.video_file_structured
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from py_lib_tooling import console
from py_lib_tooling import run_async
from workbench.llm_router.gemini_webapi._opera_cookie_client import managed_client
from workbench.llm_router.gemini_webapi._structured_output import (
    VideoObservation,
    build_rooftop_video_prompt,
    parse_model_output_json,
)

# =============================================================================
# Scenario
# =============================================================================

# Keep the shared jumper clip fixed so this script stays about the local video
# upload seam and structured-output result.
_MODEL = "gemini-3.0-flash"
_REPO_ROOT = Path(__file__).resolve().parents[3]
_VIDEO_PATH = _REPO_ROOT / "tests/llm_router/data/jumper.mp4"
_PROMPT = build_rooftop_video_prompt()
_INIT_TIMEOUT_SECONDS = 120.0


# =============================================================================
# Helpers
# =============================================================================
# No local helpers for this scenario.


# =============================================================================
# Pipeline
# =============================================================================


async def run_pipeline() -> dict[str, Any]:
    """Run the real live Gemini WebAPI video-plus-JSON flow."""
    # Build and initialize the browser-authenticated client through one shared
    # managed helper before attempting the local video upload.
    async with managed_client(init_timeout_seconds=_INIT_TIMEOUT_SECONDS) as client:
        # Upload the shared MP4 clip and validate the returned JSON before using
        # it as manual evidence.
        output = await client.generate_content(
            _PROMPT,
            files=[_VIDEO_PATH],
            model=_MODEL,
        )
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
        "Uploading the shared rooftop-jump clip through a live Gemini WebAPI "
        "session and asking for a small JSON summary.",
        details=(
            f"Model: {_MODEL}",
            f"Video: {_VIDEO_PATH.name}",
            "Why this fixture: the jump and rooftop cues are easy to inspect manually.",
        ),
    )

    result = run_async(run_pipeline())
    console.demo_step(
        "Observed Structured Video Output",
        "The live session returned JSON describing the clip's main action and "
        "location.",
        details=(
            f"action: {result['action']}",
            f"location: {result['location']}",
            "This is enough to trust that the upload and structured response "
            "both worked.",
        ),
    )
    console.print_json(result)
    console.demo_outcome(
        "Gemini WebAPI can handle real local video upload plus prompt-driven "
        "structured output in this environment.",
    )


if __name__ == "__main__":
    main()


# =============================================================================
# Expected Output
# =============================================================================
EXPECTED_OUTPUT = """
Real run on 2026-04-03:
{
  "action": "jumping",
  "evidence": [
    "person leaping over a metal railing",
    "background showing a high-altitude view of the city"
  ],
  "location": "the rooftop of a skyscraper"
}
""".strip()
