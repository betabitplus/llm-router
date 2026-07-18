# %%
"""OpenAI-compatible async text-generation workbench script.

Why:
    Shows that the `openai` SDK async client can run one plain text request
    through a real OpenAI-compatible provider with the same config knobs used
    in `src/`.

Covers:
    Area: openai-compatible live async text generation
    Behavior: async generation, temperature and seed parameters
    Interface: `AsyncOpenAI().chat.completions.create(...)`

Checks:
    If one live async plain-text request succeeds through the chat API, then the generic
        OpenAI-compatible async text path accepts the configured prompt.
    If the response exposes assistant `text`, then the manual run proves the provider
        returned usable completion content.
    If the response exposes `usage`, then the manual run also proves token accounting
        survived the live request.

Examples:
    Run manually:
        uv run python -m workbench.llm_router.openai.text_generation_async
        uv run python scripts/runtime/reproduce_running_loop.py \
            workbench.llm_router.openai.text_generation_async
"""

from __future__ import annotations

from typing import Any

from py_lib_tooling import console, run_async

from workbench.llm_router.openai._sdk_helpers import (
    build_async_client,
    provider_api_key_env,
    response_text,
    usage_snapshot,
)

# =============================================================================
# Scenario
# =============================================================================

# Keep the NVIDIA endpoint fixed here because it accepts the seeded async text
# path this probe is meant to verify.
_BASE_URL = "https://integrate.api.nvidia.com/v1"
_API_KEY_ENV = provider_api_key_env("NVIDIA")
_MODEL = "deepseek-ai/deepseek-v4-flash"
_PROMPT = "Reply with only OK."
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
    """Run one real async OpenAI-compatible text-generation request."""
    client = build_async_client(api_key_env=_API_KEY_ENV, base_url=_BASE_URL)
    response = await client.chat.completions.create(
        model=_MODEL,
        messages=[{"role": "user", "content": _PROMPT}],
        temperature=_TEMPERATURE,
        seed=_SEED,
    )
    return {
        "model": _MODEL,
        "text": response_text(response),
        "usage": usage_snapshot(response),
    }


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


async def main() -> None:
    """Run the workbench script as a narrative manual demo."""
    console.demo_intro(__doc__)
    console.demo_step(
        "Scenario",
        "Sending one plain text prompt through a live async OpenAI-compatible "
        "NVIDIA endpoint.",
        details=(
            f"Base URL: {_BASE_URL}",
            f"Model: {_MODEL}",
            f"Prompt: {_PROMPT}",
            f"Temperature: {_TEMPERATURE}",
            f"Seed: {_SEED}",
        ),
    )

    result = await run_pipeline()
    console.demo_step(
        "Observed Text Output",
        (
            "The live OpenAI-compatible async provider returned plain text and "
            "usage metadata."
        ),
        details=(
            f"text: {result['text']}",
            f"usage: {result['usage']}",
        ),
    )
    console.print_json(result)
    console.demo_outcome(
        "This is enough to trust that the generic async text path is working in "
        "this environment.",
    )


if __name__ == "__main__":
    run_async(main())


# =============================================================================
# Expected Output
# =============================================================================
EXPECTED_OUTPUT = """
Real run on 2026-04-03:
{
  "model": "deepseek-ai/deepseek-v4-flash",
  "text": "OK",
  "usage": {
    "input_tokens": 15,
    "output_tokens": 2,
    "total_tokens": 17
  }
}
""".strip()
