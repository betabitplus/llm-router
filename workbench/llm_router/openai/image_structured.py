# %%
"""OpenAI-compatible image structured-output workbench script.

Why:
    Shows that the `openai` SDK can drive a real OpenAI-compatible provider
    through one image-plus-schema call and return structured JSON.

Covers:
    Area: openai-compatible live multimodal generation
    Behavior: image input, JSON-schema output
    Interface: `OpenAI().chat.completions.create(...)`

Checks:
    If the live provider accepts the shared image fixture, then the real multimodal
        input seam is working.
    If the returned payload parses into the requested scene schema, then the structured-
        output contract is working on the live response.
    If the parsed summary exposes traffic-grounded scene fields, then the output stayed
        tied to the shared image instead of drifting into generic text.
    If the result also exposes `usage`, then the manual run keeps token accounting
        alongside the parsed scene summary.

Examples:
    Run manually:
        uv run python -m workbench.llm_router.openai.image_structured
        uv run python scripts/runtime/reproduce_running_loop.py \
            workbench.llm_router.openai.image_structured
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from py_lib_tooling import console

from workbench.llm_router.openai._sdk_helpers import (
    build_client,
    image_data_url,
    parse_message_json,
    provider_api_key_env,
    usage_snapshot,
)
from workbench.llm_router.openai._structured_output import (
    SCENE_SUMMARY_RESPONSE_FORMAT,
)

# =============================================================================
# Scenario
# =============================================================================

_REPO_ROOT = Path(__file__).resolve().parents[3]
# Keep the provider and model fixed so this script stays about the generic
# OpenAI-compatible image-plus-schema request shape.
_BASE_URL = "https://integrate.api.nvidia.com/v1"
_API_KEY_ENV = provider_api_key_env("NVIDIA")
_MODEL = "deepseek-ai/deepseek-v4-flash"
_IMAGE_PATH = _REPO_ROOT / "tests/llm_router/data/test_image.png"
# The shared traffic image makes it easy to tell whether the response stayed
# grounded in the uploaded content.
_PROMPT = (
    "Describe the attached image and return JSON.\n\n"
    "Return exactly these keys:\n"
    "- primary_subject\n"
    "- setting\n"
    "- visible_objects\n"
    "- evidence\n\n"
    "If the scene is a road, highway, or traffic setting, mention that clearly.\n"
    "Return ONLY valid JSON. No markdown."
)


# =============================================================================
# Helpers
# =============================================================================
# No local helpers for this scenario.


# =============================================================================
# Pipeline
# =============================================================================


def run_pipeline() -> dict[str, Any]:
    """Run one real OpenAI-compatible image-plus-schema request."""
    # Reuse the family helper so this probe mirrors the exact image-data-url
    # setup used by the workbench suite.
    client = build_client(api_key_env=_API_KEY_ENV, base_url=_BASE_URL)
    try:
        # Run one live image request and keep the parsed JSON plus usage as the
        # manual evidence for this seam.
        response = client.chat.completions.create(
            model=_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": _PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {"url": image_data_url(_IMAGE_PATH)},
                        },
                    ],
                }
            ],
            response_format=SCENE_SUMMARY_RESPONSE_FORMAT,
            temperature=0.0,
        )
        return {
            "parsed": parse_message_json(response),
            "usage": usage_snapshot(response),
        }
    finally:
        client.close()


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the workbench script as a narrative manual demo."""
    console.demo_intro(__doc__)
    console.demo_step(
        "Scenario",
        "Sending the shared road-traffic fixture through a live "
        "OpenAI-compatible image request.",
        details=(
            f"Base URL: {_BASE_URL}",
            f"Model: {_MODEL}",
            f"Image: {_IMAGE_PATH.name}",
        ),
    )
    console.display_image_if_available(_IMAGE_PATH)

    result = run_pipeline()
    parsed = result["parsed"]
    console.demo_step(
        "Observed Structured Output",
        "The live provider returned JSON that matches the requested road-scene schema.",
        details=(
            f"primary_subject: {parsed['primary_subject']}",
            f"setting: {parsed['setting']}",
            f"usage: {result['usage']}",
        ),
    )
    console.print_json(result)
    console.demo_outcome(
        "This is enough to trust that the generic image input and structured "
        "JSON path work in this environment.",
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
      "multiple vehicles on the road",
      "road markings and dividers",
      "grass and vegetation alongside the road"
    ],
    "primary_subject": "vehicles",
    "setting": "highway or road with traffic",
    "visible_objects": [
      "cars",
      "van"
""".strip()
