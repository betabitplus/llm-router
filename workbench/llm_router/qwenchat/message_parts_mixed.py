# %%
"""QwenChat mixed message-parts workbench script.

Why:
    Shows the non-standard QwenChat message seam where role-less input becomes
    one user message whose consecutive text chunks are merged around uploaded
    media parts.

Covers:
    Area: qwenchat message conversion
    Behavior: text buffering, mixed text and image parts
    Interface: `POST /files/upload`, `POST /chat/completions`

Checks:
    If `part_count` and `part_types` show one merged text part before the image and one
        trailing text part after it, then the mixed-content conversion kept the expected
        text-buffering shape.
    If `first_text_contains_prefix` and `first_text_contains_context` are true, then the
        leading merged text part preserved both pre-image instruction chunks.
    If `trailing_text` preserves the final instruction and the live response exposes
        `normalized_reply`, then the model still followed the post-image instruction
        after conversion.
    If the result also exposes `usage`, then the manual run keeps token accounting
        beside the mixed-part evidence.

Examples:
    Run manually:
        uv run python -m workbench.llm_router.qwenchat.message_parts_mixed
        uv run python scripts/runtime/reproduce_running_loop.py \
            workbench.llm_router.qwenchat.message_parts_mixed
"""

from __future__ import annotations

from typing import Any

from py_lib_tooling import console

from tests.llm_router.support.builders import get_llm_router_test_data_path
from workbench.llm_router.qwenchat._chat_completions import (
    build_payload,
    post_completion_sync,
    response_text,
    usage_snapshot,
)
from workbench.llm_router.qwenchat._runtime import build_sync_client, qwenchat_base_url
from workbench.llm_router.qwenchat._structured_output import (
    build_mixed_message_prompt,
    normalize_reply,
)
from workbench.llm_router.qwenchat._uploads import (
    QwenContentPart,
    build_user_content_sync,
)

# =============================================================================
# Scenario
# =============================================================================

# Keep one vision-capable model fixed so this script stays about the mixed
# message-part flattening seam around a real uploaded image.
_MODEL = "qwen3-vl-plus"
_IMAGE_FILENAME = "test_image.png"
_IMAGE_PATH = get_llm_router_test_data_path(_IMAGE_FILENAME)
_TEXT_PREFIX = "First instruction chunk: read all text instructions carefully."
_TEXT_CONTEXT = "Second instruction chunk: the image should show a traffic scene."
_FINAL_PROMPT = build_mixed_message_prompt()
_TEMPERATURE = 0.0
_SEED = 42


# =============================================================================
# Helpers
# =============================================================================


def _text_part_text(part: QwenContentPart, *, context: str) -> str:
    """Return text from one known text part and fail loudly otherwise."""
    if part["type"] != "text":
        msg = f"The live mixed-message scenario did not produce a text {context}."
        raise TypeError(msg)
    return part["text"]


# =============================================================================
# Pipeline
# =============================================================================


def run_pipeline() -> dict[str, Any]:
    """Run one real QwenChat mixed text-and-image request."""
    # Build the mixed role-less content first so the manual output can show the
    # actual merged part layout before the live completion call.
    with build_sync_client() as client:
        user_content = build_user_content_sync(
            client=client,
            items=[
                _TEXT_PREFIX,
                _TEXT_CONTEXT,
                _IMAGE_PATH,
                _FINAL_PROMPT,
            ],
        )
        response = post_completion_sync(
            client=client,
            payload=build_payload(
                model=_MODEL,
                user_content=user_content,
                temperature=_TEMPERATURE,
                seed=_SEED,
            ),
        )

    if not isinstance(user_content, list):
        msg = "The live mixed-message scenario did not produce a mixed content list."
        raise TypeError(msg)

    reply = response_text(response)
    return {
        "reply": reply,
        "normalized_reply": normalize_reply(reply),
        "part_count": len(user_content),
        "part_types": [str(part["type"]) for part in user_content],
        "first_text_contains_prefix": _TEXT_PREFIX
        in _text_part_text(user_content[0], context="prefix part"),
        "first_text_contains_context": _TEXT_CONTEXT
        in _text_part_text(user_content[0], context="prefix part"),
        "trailing_text": _text_part_text(user_content[-1], context="trailing part"),
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
        (
            "Sending multiple text chunks and one image through the "
            "role-less QwenChat message converter."
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
        "Observed Mixed User Content",
        (
            "The live request used merged text around the uploaded image "
            "and still followed the final instruction."
        ),
        details=(
            f"part_types: {result['part_types']}",
            f"normalized_reply: {result['normalized_reply']}",
            f"first_text_contains_prefix: {result['first_text_contains_prefix']}",
            f"first_text_contains_context: {result['first_text_contains_context']}",
        ),
    )
    console.print_json(result)
    console.demo_outcome(
        "This is enough to trust that the non-standard QwenChat mixed-message "
        "part conversion works in this environment.",
    )


if __name__ == "__main__":
    main()


# =============================================================================
# Expected Output
# =============================================================================
EXPECTED_OUTPUT = """
Real run on 2026-04-13 (excerpt):
{
  "first_text_contains_context": true,
  "first_text_contains_prefix": true,
  "normalized_reply": "road-ok",
  "part_count": 3,
  "part_types": [
    "text",
    "image",
    "text"
  ],
  "usage": {
    "input_tokens": 259,
    "output_tokens": 3,
    "total_tokens": 262
  }
}
""".strip()
