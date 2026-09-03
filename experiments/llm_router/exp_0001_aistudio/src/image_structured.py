# %%
"""AI Studio image structured-output experiment script.

Why:
    Shows that AI Studio can accept an image on the OpenAI-compatible path and
    return structured JSON through the same non-video endpoint.

Covers:
    Area: AI Studio non-video path
    Behavior: image input, structured output
    Interface: `OpenAI().chat.completions.create(...)`

Checks:
    If the AI Studio non-video path accepts the shared image fixture, then the real
        multimodal input seam is working.
    If the returned payload parses into the requested scene schema, then the structured-
        output contract is working on the live response.
    If the parsed summary exposes traffic-grounded scene fields, then the output stayed
        tied to the shared image instead of drifting into generic text.
    If the result also exposes `usage`, then the manual run keeps token accounting
        alongside the parsed scene summary.

Examples:
    From this capsule root:
        uv run --locked --managed-python python src/image_structured.py
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from _json_schema import build_resolved_response_format
from _sdk_helpers import (
    build_client,
    image_data_url,
    parse_message_json,
    usage_snapshot,
)
from _structured_output import (
    SceneSummary,
    build_scene_summary_prompt,
)
from py_lib_testkit import console

# =============================================================================
# Scenario
# =============================================================================

_CAPSULE_ROOT = Path(__file__).resolve().parent.parent
# Keep the stable smoke model and shared traffic image fixed so the manual result
# focuses on the AI Studio non-video image path.
_MODEL = "gemini-3.5-flash-lite"
_IMAGE_PATH = _CAPSULE_ROOT / "inputs/test_image.png"
_SYSTEM_PROMPT = "Follow instructions exactly. Reply with only what is asked."
_PROMPT = build_scene_summary_prompt()


# =============================================================================
# Helpers
# =============================================================================
# No local helpers for this scenario.


# =============================================================================
# Pipeline
# =============================================================================


def run_pipeline() -> dict[str, Any]:
    """Run one real AI Studio image-plus-JSON request."""
    # Build the AI Studio client on its OpenAI-compatible non-video path.
    client = build_client()
    # Send the shared image through the same content-part layout this suite
    # uses elsewhere, then validate the returned JSON.
    response = client.chat.completions.create(
        model=_MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": _SYSTEM_PROMPT},
                    {"type": "text", "text": _PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": image_data_url(_IMAGE_PATH)},
                    },
                ],
            }
        ],
        response_format=build_resolved_response_format(SceneSummary),
        temperature=0.0,
    )
    parsed = SceneSummary.model_validate(parse_message_json(response))
    return {
        "parsed": parsed.model_dump(mode="json"),
        "usage": usage_snapshot(response),
    }


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the experiment script as a narrative manual demo."""
    console.demo_intro(__doc__)
    console.demo_step(
        "Scenario",
        "Sending the shared road-traffic image through the AI Studio "
        "OpenAI-compatible endpoint and asking for structured JSON.",
        details=(
            f"Model: {_MODEL}",
            f"Image: {_IMAGE_PATH.name}",
            (
                "Why this setup: it proves the AI Studio non-video image path on "
                "its own, separate from the generic experiment suite."
            ),
        ),
    )
    console.display_image_if_available(_IMAGE_PATH)

    result = run_pipeline()
    parsed = result["parsed"]
    console.demo_step(
        "Observed Structured Output",
        "The live AI Studio image path returned the expected structured scene summary.",
        details=(
            f"primary_subject: {parsed['primary_subject']}",
            f"setting: {parsed['setting']}",
            f"usage: {result['usage']}",
        ),
    )
    console.print_json(result)
    console.demo_outcome(
        "This is enough to trust that the AI Studio non-video image path works "
        "in this environment.",
    )


if __name__ == "__main__":
    main()


# =============================================================================
# Expected Output
# =============================================================================
EXPECTED_OUTPUT = """
Real run on 2026-04-13 (excerpt, cut after 12 lines):
{
  "parsed": {
    "evidence": [
      "multiple vehicles are driving on the road",
      "white dashed lines separate the lanes",
      "a blue sign with '100 m' is visible on the right"
    ],
    "primary_subject": "Vehicles on a highway",
    "setting": "A multi-lane highway with traffic",
    "visible_objects": [
      "cars",
      "white van"
""".strip()
