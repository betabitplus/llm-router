# %%
"""Gemini WebAPI async retry text-generation workbench script.

Why:
    Shows the Tenacity retry contract used by the browser-backed Gemini
    adapter on one real async text request.

Covers:
    Area: gemini-webapi live async retry policy
    Behavior: Tenacity retry wrapper around one SDK text request
    Interface: `GeminiClient.init()` and `await GeminiClient.generate_content()`

Checks:
    If the result exposes `retryable_exceptions` and `retry_policy`, then the script is
        probing the same retry contract used by `src/`.
    If the result exposes `attempt_count` and `retry_events`, then the manual run can
        show whether the live request succeeded immediately or only after retries.
    If the retried call still returns assistant `text`, then the retry wrapper preserved
        a usable successful response.

Examples:
    Run manually:
        uv run python -m workbench.llm_router.gemini_webapi.retry_text_generation_async
        uv run python scripts/runtime/reproduce_running_loop.py \
            workbench.llm_router.gemini_webapi.retry_text_generation_async
"""

from __future__ import annotations

from typing import Any

import tenacity
from gemini_webapi.exceptions import APIError, TimeoutError as GeminiTimeoutError
from py_lib_tooling import console, run_async

from workbench.llm_router._retry_demo import (
    build_retry_params,
    event_dicts,
    exception_type_names,
)
from workbench.llm_router.gemini_webapi._opera_cookie_client import managed_client

# =============================================================================
# Scenario
# =============================================================================

# Keep the same tiny prompt and flash model as the plain text probe so this
# script isolates the retry wrapper around the browser-backed async call.
_MODEL = "gemini-3.0-flash"
_PROMPT = "Reply with only OK."
_INIT_TIMEOUT_SECONDS = 30.0
_MAX_ATTEMPTS = 3
_MIN_WAIT_SECONDS = 1.0
_MAX_WAIT_SECONDS = 8.0
_RETRYABLE_EXCEPTIONS = (APIError, GeminiTimeoutError)


# =============================================================================
# Helpers
# =============================================================================

# No local helpers for this scenario.


# =============================================================================
# Pipeline
# =============================================================================


async def run_pipeline() -> dict[str, Any]:
    """Run one live async Gemini WebAPI request behind Tenacity."""
    retry_events = []
    attempt_count = 0

    async with managed_client(init_timeout_seconds=_INIT_TIMEOUT_SECONDS) as client:

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
            """Execute one live Gemini WebAPI request."""
            nonlocal attempt_count
            attempt_count += 1
            return await client.generate_content(_PROMPT, model=_MODEL)

        output = await _call()

    return {
        "model": _MODEL,
        "attempt_count": attempt_count,
        "retryable_exceptions": exception_type_names(_RETRYABLE_EXCEPTIONS),
        "retry_policy": {
            "max_attempts": _MAX_ATTEMPTS,
            "min_wait_seconds": _MIN_WAIT_SECONDS,
            "max_wait_seconds": _MAX_WAIT_SECONDS,
        },
        "retry_events": event_dicts(retry_events),
        "text": output.text.strip(),
    }


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the workbench script as a narrative manual demo."""
    console.demo_intro(__doc__)
    console.demo_step(
        "Scenario",
        "Starting one real Gemini WebAPI session from local Opera cookies and "
        "wrapping the async text call in the same Tenacity exception set used "
        "in `src/`.",
        details=(
            f"Model: {_MODEL}",
            f"Prompt: {_PROMPT}",
            f"Retryable exceptions: {exception_type_names(_RETRYABLE_EXCEPTIONS)}",
        ),
    )

    result = run_async(run_pipeline())
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
        "This is enough to trust the Gemini WebAPI Tenacity exception policy "
        "around the async text path in this environment.",
    )


if __name__ == "__main__":
    main()


# =============================================================================
# Expected Output
# =============================================================================
EXPECTED_OUTPUT = """
Real run on 2026-04-03:
{
  "attempt_count": 1,
  "model": "gemini-3.0-flash",
  "retry_events": [],
  "retry_policy": {
    "max_attempts": 3,
    "max_wait_seconds": 8.0,
    "min_wait_seconds": 1.0
  },
  "retryable_exceptions": [
    "APIError",
    "TimeoutError"
  ],
  "text": "OK"
}
""".strip()
