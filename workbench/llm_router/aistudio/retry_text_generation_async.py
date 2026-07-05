# %%
"""AI Studio async retry text-generation workbench script.

Why:
    Shows the Tenacity retry contract used by the AI Studio non-video
    OpenAI-compatible text path on a real async request.

Covers:
    Area: AI Studio non-video async retry policy
    Behavior: Tenacity retry wrapper around one async text request
    Interface: `AsyncOpenAI().chat.completions.create(...)`

Checks:
    If the result exposes `retryable_exceptions` and `retry_policy`, then the script is
        probing the same retry contract used by `src/`.
    If the result exposes `attempt_count` and `retry_events`, then the manual run can
        show whether the live request succeeded immediately or only after retries.
    If the retried call still returns assistant `text` and `usage`, then the retry
        wrapper preserved a usable successful response.

Examples:
    Run manually:
        uv run python -m workbench.llm_router.aistudio.retry_text_generation_async
        uv run python scripts/runtime/reproduce_running_loop.py \
            workbench.llm_router.aistudio.retry_text_generation_async
"""

from __future__ import annotations

from typing import Any

import tenacity
from openai import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    RateLimitError,
)
from py_lib_tooling import console, run_async

from workbench.llm_router._retry_demo import (
    build_retry_params,
    event_dicts,
    exception_type_names,
)
from workbench.llm_router.aistudio._sdk_helpers import (
    build_async_client,
    openai_base_url,
    response_text,
    usage_snapshot,
)

# =============================================================================
# Scenario
# =============================================================================

# Keep the baseline non-video flash model fixed so this script isolates the
# retry wrapper around AI Studio's OpenAI-compatible text path.
_BASE_URL = openai_base_url()
_MODEL = "gemini-2.5-flash"
_PROMPT = "Reply with only OK."
_MAX_ATTEMPTS = 3
_MIN_WAIT_SECONDS = 1.0
_MAX_WAIT_SECONDS = 8.0
_RETRYABLE_EXCEPTIONS = (
    RateLimitError,
    APITimeoutError,
    InternalServerError,
    APIConnectionError,
)


# =============================================================================
# Helpers
# =============================================================================

# No local helpers for this scenario.


# =============================================================================
# Pipeline
# =============================================================================


async def run_pipeline() -> dict[str, Any]:
    """Run one live async AI Studio request behind Tenacity."""
    client = build_async_client()
    retry_events = []
    attempt_count = 0

    @tenacity.retry(
        **build_retry_params(
            retry=tenacity.retry_if_exception_type(_RETRYABLE_EXCEPTIONS),
            events=retry_events,
            max_attempts=_MAX_ATTEMPTS,
            min_wait_seconds=_MIN_WAIT_SECONDS,
            max_wait_seconds=_MAX_WAIT_SECONDS,
        )
    )
    async def _call() -> object:
        """Execute one live AI Studio non-video request."""
        nonlocal attempt_count
        attempt_count += 1
        return await client.chat.completions.create(
            model=_MODEL,
            messages=[{"role": "user", "content": _PROMPT}],
            temperature=0.0,
        )

    try:
        response = await _call()
    finally:
        await client.close()

    return {
        "base_url": _BASE_URL,
        "model": _MODEL,
        "attempt_count": attempt_count,
        "retryable_exceptions": exception_type_names(_RETRYABLE_EXCEPTIONS),
        "retry_policy": {
            "max_attempts": _MAX_ATTEMPTS,
            "min_wait_seconds": _MIN_WAIT_SECONDS,
            "max_wait_seconds": _MAX_WAIT_SECONDS,
        },
        "retry_events": event_dicts(retry_events),
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
        "Sending one tiny async text request through the AI Studio non-video "
        "OpenAI-compatible path with the same Tenacity exception set used by "
        "that branch in `src/`.",
        details=(
            f"Base URL: {_BASE_URL}",
            f"Model: {_MODEL}",
            f"Prompt: {_PROMPT}",
            f"Retryable exceptions: {exception_type_names(_RETRYABLE_EXCEPTIONS)}",
        ),
    )

    result = await run_pipeline()
    console.demo_step(
        "Observed Retry Contract",
        "The live request finished and reported the retry policy plus any real "
        "retry events that occurred before success.",
        details=(
            f"attempt_count: {result['attempt_count']}",
            f"retry_events: {result['retry_events']}",
            f"text: {result['text']}",
        ),
    )
    console.print_json(result)
    console.demo_outcome(
        "This is enough to trust the AI Studio non-video Tenacity exception "
        "policy around the async text path in this environment.",
    )


if __name__ == "__main__":
    run_async(main())


# =============================================================================
# Expected Output
# =============================================================================
EXPECTED_OUTPUT = """
Real run on 2026-04-03 (excerpt, key verification fields):
{
  "attempt_count": 1,
  "retry_events": [],
  "retryable_exceptions": [
    "RateLimitError",
    "APITimeoutError",
    "InternalServerError",
    "APIConnectionError"
  ],
  "text": "OK"
}
""".strip()
