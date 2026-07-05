# %%
"""Gemini WebAPI image structured-output workbench script.

Why:
    Shows that `gemini-webapi` can combine one real image upload with a
    prompt-driven JSON response that stays easy to inspect manually.

Covers:
    Area: gemini-webapi live multimodal generation
    Behavior: image input, prompt-driven structured output
    Interface: `GeminiClient.generate_content(..., files=[...])`

Checks:
    If the browser-authenticated session accepts the shared image fixture, then the real
        multimodal input seam is working.
    If the returned payload parses into the requested scene schema, then the structured-
        output contract is working on the live response.
    If the parsed summary exposes traffic-grounded scene fields, then the output stayed
        tied to the shared image instead of drifting into generic text.

Examples:
    Run manually:
        uv run python -m workbench.llm_router.gemini_webapi.image_structured
        uv run python scripts/runtime/reproduce_running_loop.py \
            workbench.llm_router.gemini_webapi.image_structured
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from py_lib_tooling import console, run_async

from workbench.llm_router.gemini_webapi._opera_cookie_client import managed_client
from workbench.llm_router.gemini_webapi._structured_output import (
    TrafficSceneSummary,
    build_scene_summary_prompt,
    parse_model_output_json,
)

# =============================================================================
# Scenario
# =============================================================================

# Keep the shared traffic image fixed so the manual result can focus on the
# upload-plus-JSON seam rather than changing scene content.
_MODEL = "gemini-3.0-flash"
_REPO_ROOT = Path(__file__).resolve().parents[3]
_IMAGE_PATH = _REPO_ROOT / "tests/llm_router/data/test_image.png"
_PROMPT = build_scene_summary_prompt()


# =============================================================================
# Helpers
# =============================================================================
# No local helpers for this scenario.


# =============================================================================
# Pipeline
# =============================================================================


async def run_pipeline() -> dict[str, Any]:
    """Run the real live Gemini WebAPI image-plus-JSON flow."""
    # Build and initialize the browser-authenticated client through one shared
    # managed helper before attempting the file-grounded JSON request.
    async with managed_client(init_timeout_seconds=30.0) as client:
        # Upload the shared image and validate the returned JSON so the manual
        # walkthrough stays tied to a real structured-output seam.
        output = await client.generate_content(
            _PROMPT,
            files=[_IMAGE_PATH],
            model=_MODEL,
        )
        parsed = TrafficSceneSummary.model_validate(
            parse_model_output_json(output.text)
        )
        return parsed.model_dump(mode="json")


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the workbench script as a narrative manual demo."""
    console.demo_intro(__doc__)
    console.demo_step(
        "Scenario",
        "Sending the shared road-traffic image through a live Gemini WebAPI "
        "session and asking for a JSON scene summary.",
        details=(
            f"Model: {_MODEL}",
            f"Image: {_IMAGE_PATH.name}",
            "Why this prompt: it keeps the result grounded and easy to inspect "
            "manually.",
        ),
    )
    console.display_image_if_available(_IMAGE_PATH)

    result = run_async(run_pipeline())
    console.demo_step(
        "Observed Structured Output",
        "The live session returned JSON matching the requested traffic-scene shape.",
        details=(
            f"primary_subject: {result['primary_subject']}",
            f"setting: {result['setting']}",
            "This is enough to trust that the model followed both the image "
            "and the requested JSON shape.",
        ),
    )
    console.print_json(result)
    console.demo_outcome(
        "Gemini WebAPI can combine real image upload with prompt-driven "
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
  "evidence": [
    "multiple cars traveling in the same direction across dashed lane markers",
    "blue distance marker sign on the right shoulder"
  ],
  "primary_subject": "highway traffic flow",
  "setting": "multi-lane asphalt highway on a sunny day",
  "visible_objects": [
    "white van",
    "red hatchback",
    "dark blue station wagon",
    "lane markings",
""".strip()
