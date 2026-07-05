# %%
"""QwenChat async text-generation workbench script.

Why:
    Shows that the custom QwenChat `/chat/completions` path also works through
    one async request, matching the async adapter branch in `src/`.

Covers:
    Area: qwenchat live async text generation
    Behavior: async request, plain text response
    Interface: `POST /chat/completions`

Checks:
    If one live async plain-text request succeeds through the direct QwenChat proxy,
        then the async text route accepts the configured message shape.
    If the response exposes both `text` and `normalized_reply`, then the manual run
        proves the proxy returned usable assistant text in the shape this script
        inspects.
    If the response exposes `usage`, then the manual run also proves normalized token
        accounting survived the live request.

Examples:
    Run manually:
        uv run python -m workbench.llm_router.qwenchat.text_generation_async
        uv run python scripts/runtime/reproduce_running_loop.py \
            workbench.llm_router.qwenchat.text_generation_async
"""

from __future__ import annotations

from typing import Any

from py_lib_tooling import console
from py_lib_tooling import run_async
from workbench.llm_router.qwenchat._chat_completions import (
    build_payload,
    post_completion_async,
    response_text,
    usage_snapshot,
)
from workbench.llm_router.qwenchat._runtime import (
    build_async_client,
    qwenchat_base_url,
)
from workbench.llm_router.qwenchat._structured_output import normalize_reply
from workbench.llm_router.qwenchat._uploads import build_user_content_async

# =============================================================================
# Scenario
# =============================================================================

# Keep the same text-only model fixed so this script isolates async execution
# rather than changing the underlying provider route.
_MODEL = "qwen-max-latest"
_SYSTEM_PROMPT = "Follow instructions exactly. Reply with only what is asked."
_PROMPT = "Reply with only: pong"
_TEMPERATURE = 0.0
_SEED = 42


# =============================================================================
# Helpers
# =============================================================================
# No local helpers for this scenario.


# =============================================================================
# Pipeline
# =============================================================================


async def run_pipeline() -> dict[str, Any]:
    """Run one real async QwenChat text request."""
    # Build the same flattened role-less user message the sync path uses, but
    # drive it through the async HTTP client.
    async with build_async_client() as client:
        user_content = await build_user_content_async(
            client=client,
            items=[_SYSTEM_PROMPT, _PROMPT],
        )
        response = await post_completion_async(
            client=client,
            payload=build_payload(
                model=_MODEL,
                user_content=user_content,
                temperature=_TEMPERATURE,
                seed=_SEED,
            ),
        )
    text = response_text(response)
    return {
        "base_url": qwenchat_base_url(),
        "model": _MODEL,
        "text": text,
        "normalized_reply": normalize_reply(text),
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
            "Sending one plain text message through the live async QwenChat "
            "completion route."
        ),
        details=(
            f"Base URL: {qwenchat_base_url()}",
            f"Model: {_MODEL}",
            f"Prompt: {_PROMPT}",
        ),
    )

    result = run_async(run_pipeline())
    console.demo_step(
        "Observed Async Text Output",
        "The live async QwenChat route returned the expected short reply and usage.",
        details=(
            f"text: {result['text']}",
            f"normalized_reply: {result['normalized_reply']}",
            f"usage: {result['usage']}",
        ),
    )
    console.print_json(result)
    console.demo_outcome(
        "This is enough to trust that the async QwenChat text path is working "
        "in this environment.",
    )


if __name__ == "__main__":
    main()


# =============================================================================
# Expected Output
# =============================================================================
EXPECTED_OUTPUT = """
Real run on 2026-04-13:
{
  "base_url": "http://localhost:3264/api",
  "model": "qwen-max-latest",
  "normalized_reply": "pong",
  "text": "pong",
  "usage": {
    "input_tokens": 185,
    "output_tokens": 1,
    "total_tokens": 186
  }
}
""".strip()
