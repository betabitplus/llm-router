# %%
"""QwenChat image structured-output workbench script.

Why:
    Shows that QwenChat uploads one real image first, injects the returned URL
    into the mixed content payload, and still returns structured JSON.

Covers:
    Area: qwenchat live image input
    Behavior: image upload, mixed content payload, structured output
    Interface: `POST /files/upload`, `POST /chat/completions`

Checks:
    If the direct QwenChat proxy accepts the shared image upload, then the upload-plus-
        structured input seam is working.
    If `primary_subject` and `setting` stay grounded in the road-traffic fixture, then
        the parsed summary is tied to the uploaded image.
    If the result also exposes `attempts` and `usage`, then the manual run shows how the
        structured path completed and what token accounting it returned.

Examples:
    Run manually:
        uv run python -m workbench.llm_router.qwenchat.image_structured
        uv run python scripts/runtime/reproduce_running_loop.py \
            workbench.llm_router.qwenchat.image_structured
"""

from __future__ import annotations

from typing import Any

from tests.llm_router.support.builders import get_llm_router_test_data_path
from py_lib_tooling import console
from workbench.llm_router.qwenchat._runtime import build_sync_client, qwenchat_base_url
from workbench.llm_router.qwenchat._structured_output import (
    SceneSummary,
    build_scene_summary_prompt,
)
from workbench.llm_router.qwenchat._structured_runner import (
    StructuredRunConfig,
    run_structured_sync,
)

# =============================================================================
# Scenario
# =============================================================================

# Keep the vision-capable Qwen model fixed so this script isolates the image
# upload seam rather than general text behavior.
_MODEL = "qwen3-vl-plus"
_IMAGE_FILENAME = "test_image.png"
_IMAGE_PATH = get_llm_router_test_data_path(_IMAGE_FILENAME)
_SYSTEM_PROMPT = "Follow instructions exactly. Reply with only what is asked."
_PROMPT = build_scene_summary_prompt()
_TEMPERATURE = 0.0
_SEED = 42


# =============================================================================
# Helpers
# =============================================================================
# No local helpers for this scenario.


# =============================================================================
# Pipeline
# =============================================================================


def run_pipeline() -> dict[str, Any]:
    """Run one real QwenChat image-plus-structured request."""
    # Send a real PIL image through the upload-first path so the resulting JSON
    # proves both the upload and structured-output seams together.
    with build_sync_client() as client:
        result = run_structured_sync(
            client=client,
            config=StructuredRunConfig(
                model=_MODEL,
                base_items=[
                    _SYSTEM_PROMPT,
                    _PROMPT,
                    _IMAGE_PATH,
                ],
                schema_model=SceneSummary,
                temperature=_TEMPERATURE,
                seed=_SEED,
            ),
        )

    parsed = result["parsed"]
    return {
        "attempts": result["attempts"],
        "parsed": parsed,
        "usage": result["usage"],
        "primary_subject": parsed["primary_subject"],
        "setting": parsed["setting"],
    }


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the workbench script as a narrative manual demo."""
    console.demo_intro(__doc__)
    console.demo_step(
        "Scenario",
        (
            "Uploading the shared road-traffic image through live QwenChat "
            "and asking for structured scene JSON."
        ),
        details=(
            f"Base URL: {qwenchat_base_url()}",
            f"Model: {_MODEL}",
            f"Image: {_IMAGE_PATH.name}",
        ),
    )
    console.display_image_if_available(_IMAGE_PATH)

    result = run_pipeline()
    console.demo_step(
        "Observed Structured Image Output",
        (
            "The live response returned a grounded scene summary after the "
            "image upload step."
        ),
        details=(
            f"primary_subject: {result['primary_subject']}",
            f"setting: {result['setting']}",
            f"attempts: {result['attempts']}",
        ),
    )
    console.print_json(result)
    console.demo_outcome(
        "This is enough to trust that the QwenChat image upload and structured "
        "JSON path work in this environment.",
    )


if __name__ == "__main__":
    main()


# =============================================================================
# Expected Output
# =============================================================================
EXPECTED_OUTPUT = """
Real run on 2026-04-13 (excerpt):
{
  "attempts": 1,
  "primary_subject": "multiple vehicles traveling on a multi-lane highway",
  "setting": "a sunny daytime highway with green roadside vegetation",
  "usage": {
    "input_tokens": 505,
    "output_tokens": 67,
    "total_tokens": 572
  }
}
""".strip()
