# %%
"""Google GenAI image structured-output workbench script.

Why:
    Shows that the native Google client accepts a real PIL image directly and
    returns parsed structured output from one live request.

Covers:
    Area: google-genai live multimodal generation
    Behavior: direct image input, structured output
    Interface: `Client.models.generate_content(...)`

Checks:
    If the native Google client accepts the shared image fixture, then the real
        multimodal input seam is working.
    If the returned payload parses into the requested scene schema, then the structured-
        output contract is working on the live response.
    If the parsed summary exposes traffic-grounded scene fields, then the output stayed
        tied to the shared image instead of drifting into generic text.
    If the result also exposes `usage`, then the manual run keeps token accounting
        alongside the parsed scene summary.

Examples:
    Run manually:
        uv run python -m workbench.llm_router.google_genai.image_structured
        uv run python scripts/runtime/reproduce_running_loop.py \
            workbench.llm_router.google_genai.image_structured
"""

from __future__ import annotations

from typing import Any

from google.genai import types
from py_lib_tooling import console

from tests.llm_router.support.builders import build_test_image
from workbench.llm_router.google_genai._sdk_helpers import (
    build_client,
    parsed_response_dict,
    usage_snapshot,
)
from workbench.llm_router.google_genai._structured_output import (
    TrafficSceneSummary,
    build_scene_summary_prompt,
)

# =============================================================================
# Scenario
# =============================================================================

# Keep the same preview model and shared image fixture the adapter path expects
# so the direct-image SDK seam stays easy to inspect.
_MODEL = "gemini-2.5-flash"
_IMAGE_FILENAME = "test_image.png"
_PROMPT = build_scene_summary_prompt()


# =============================================================================
# Helpers
# =============================================================================
# No local helpers for this scenario.


# =============================================================================
# Pipeline
# =============================================================================


def run_pipeline() -> dict[str, Any]:
    """Run one real native Google image-plus-schema request."""
    # Build the native SDK client exactly as this workbench family uses it.
    client = build_client()
    # Send the PIL image directly, then keep the parsed JSON plus usage as the
    # manual evidence for this direct-image seam.
    response = client.models.generate_content(
        model=_MODEL,
        contents=[_PROMPT, build_test_image(_IMAGE_FILENAME)],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=TrafficSceneSummary,
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
        "Sending the shared road-traffic image directly as a PIL image into the "
        "native Google client.",
        details=(
            f"Model: {_MODEL}",
            f"Image: {_IMAGE_FILENAME}",
            "Why this shape: it matches the direct image item seam the adapter uses.",
        ),
    )

    result = run_pipeline()
    parsed = result["parsed"]
    console.demo_step(
        "Observed Structured Output",
        "The live Google model returned parsed structured output for the image.",
        details=(
            f"primary_subject: {parsed['primary_subject']}",
            f"setting: {parsed['setting']}",
            f"usage: {result['usage']}",
        ),
    )
    console.print_json(result)
    console.demo_outcome(
        "This is enough to trust that the native Google image path and parsed "
        "schema output both work in this environment.",
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
    "evidence": [
      "Multiple vehicles are driving on the asphalt road",
      "White dashed lines separate the lanes",
      "A blue road sign with '100' is visible on the right"
    ],
    "primary_subject": "Traffic on a highway",
    "setting": "A multi-lane highway with vehicles",
    "visible_objects": [
      "cars",
      "van",
""".strip()
