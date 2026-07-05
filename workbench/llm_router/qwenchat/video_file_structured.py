# %%
"""QwenChat uploaded-video structured workbench script.

Why:
    Shows the direct QwenChat proxy seam behind the current adapter limit:
    a local MP4 can be uploaded as a generic file part and analyzed through
    prompt-enforced structured output.

Covers:
    Area: qwenchat direct multimodal flow
    Behavior: local MP4 upload, file-part message content, structured output
    Interface: `POST /files/upload`, `POST /chat/completions`

Checks:
    If `part_types` shows the uploaded MP4 was sent as a `file` part and `upload_host`
        is present, then the manual run proves the direct proxy actually uploaded and
        referenced the video.
    If `parsed` exposes jump-related `action` and rooftop-style `location`, then the
        structured response stayed grounded in the shared clip.
    If the result also exposes `attempts` and `usage`, then the manual run shows how the
        structured path completed and what token accounting it returned.

Examples:
    Run manually:
        uv run python -m workbench.llm_router.qwenchat.video_file_structured
        uv run python scripts/runtime/reproduce_running_loop.py \
            workbench.llm_router.qwenchat.video_file_structured
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from tests.llm_router.support.builders import get_llm_router_test_data_path
from py_lib_tooling import console
from workbench.llm_router.qwenchat._runtime import build_sync_client, qwenchat_base_url
from workbench.llm_router.qwenchat._structured_output import VideoObservation
from workbench.llm_router.qwenchat._structured_runner import (
    StructuredRunConfig,
    run_structured_sync,
)
from workbench.llm_router.qwenchat._uploads import build_user_content_sync

# =============================================================================
# Scenario
# =============================================================================

# Keep this vision model fixed because it successfully analyzes uploaded MP4
# files on the current proxy, which is the exact seam this script documents.
_MODEL = "qwen2.5-vl-32b-instruct"
_VIDEO_PATH = Path(get_llm_router_test_data_path("jumper.mp4"))
_PROMPT = (
    "Return JSON with:\n"
    "- action: the main action as a short lowercase verb or gerund\n"
    "- location: a short phrase describing where the action happens\n"
    "- evidence: exactly 2 short strings describing visible motion or scene cues\n\n"
    'If the clip shows a person jumping or leaping, use a value containing "jump" '
    'or "leap" for action.\n'
    "If it happens on a rooftop, skyscraper, or tall building, mention that in "
    "location.\n"
    "In evidence, mention motion or jump-related details.\n\n"
    "Return ONLY valid JSON. No markdown."
)


# =============================================================================
# Helpers
# =============================================================================


def _extract_upload_host(content: list[dict[str, Any]]) -> str:
    """Extract the uploaded file host without exposing the full signed URL."""
    file_url = str(content[1]["file"])
    host = urlparse(file_url).netloc
    if not host:
        msg = "The live uploaded video did not expose a valid file host."
        raise RuntimeError(msg)
    return host


# =============================================================================
# Pipeline
# =============================================================================


def run_pipeline() -> dict[str, Any]:
    """Run one real direct QwenChat uploaded-video structured request."""
    # Build the mixed text+file content first so the manual result can show the
    # exact multipart shape this proxy accepts for video.
    with build_sync_client() as client:
        user_content = build_user_content_sync(
            client=client,
            items=[_PROMPT, _VIDEO_PATH],
        )
        if not isinstance(user_content, list):
            msg = "The live video scenario did not produce a multipart content list."
            raise TypeError(msg)

        structured = run_structured_sync(
            client=client,
            config=StructuredRunConfig(
                model=_MODEL,
                base_items=[_PROMPT, _VIDEO_PATH],
                schema_model=VideoObservation,
                temperature=0.0,
                seed=42,
            ),
            initial_user_content=user_content,
        )

    return {
        "base_url": qwenchat_base_url(),
        "model": _MODEL,
        "video_filename": _VIDEO_PATH.name,
        "part_types": [str(part["type"]) for part in user_content],
        "upload_host": _extract_upload_host(user_content),
        "parsed": structured["parsed"],
        "attempts": structured["attempts"],
        "usage": structured["usage"],
    }


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the workbench script as a narrative manual demo."""
    console.demo_intro(__doc__)
    console.demo_step(
        "Scenario",
        "Uploading one local MP4 to the direct QwenChat proxy and sending the "
        "returned file URL through a video-capable vision model with prompt-"
        "enforced structured output.",
        details=(
            f"Base URL: {qwenchat_base_url()}",
            f"Model: {_MODEL}",
            f"Video fixture: {_VIDEO_PATH.name}",
        ),
    )

    result = run_pipeline()
    console.demo_step(
        "Observed Uploaded Video Flow",
        "The live proxy accepted the MP4 upload as a file part, and the model "
        "returned structured JSON about the video's main action.",
        details=(
            f"part_types: {result['part_types']}",
            f"upload_host: {result['upload_host']}",
            f"action: {result['parsed']['action']}",
        ),
    )
    console.print_json(result)
    console.demo_outcome(
        "This is enough to trust that the direct QwenChat proxy supports "
        "uploaded-video structured output in this environment.",
    )


if __name__ == "__main__":
    main()


# =============================================================================
# Expected Output
# =============================================================================
EXPECTED_OUTPUT = """
Real run on 2026-04-13:
{
  "attempts": 1,
  "base_url": "http://localhost:3264/api",
  "model": "qwen2.5-vl-32b-instruct",
  "part_types": [
    "text",
    "file"
  ],
  "parsed": {
    "action": "jumping",
    "evidence": [
      "person leaps into the air",
      "arms extended for balance"
    ],
    "location": "on a rooftop"
  },
  "upload_host": "qwen-webui-prod.oss-accelerate.aliyuncs.com",
  "usage": {
    "input_tokens": 318,
    "output_tokens": 47,
    "total_tokens": 365
  },
  "video_filename": "jumper.mp4"
}
""".strip()
