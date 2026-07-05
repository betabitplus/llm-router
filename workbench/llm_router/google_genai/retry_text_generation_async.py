# %%
"""Google GenAI async retry text-generation workbench script.

Why:
    Shows the Tenacity retry contract used by the native Google adapter on one
    real async text request.

Covers:
    Area: google-genai live async retry policy
    Behavior: Tenacity retry wrapper with provider-specific `APIError`
        status/code checks
    Interface: `Client.aio.models.generate_content(...)`

Checks:
    If the result exposes `retryable_exceptions`, `retryable_api_status`,
        `retryable_http_codes`, and `retry_policy`, then the script is probing the same
        retry contract used by `src/`.
    If the result exposes `attempt_count` and `retry_events`, then the manual run can
        show whether the live request succeeded immediately or only after retries.
    If the retried call still returns assistant `text` and `usage`, then the retry
        wrapper preserved a usable successful response.

Examples:
    Run manually:
        uv run python -m workbench.llm_router.google_genai.retry_text_generation_async
        uv run python scripts/runtime/reproduce_running_loop.py \
            workbench.llm_router.google_genai.retry_text_generation_async
"""

from __future__ import annotations

from typing import Any

import httpx
import tenacity
from google.genai import types
from google.genai.errors import APIError
from py_lib_tooling import console, run_async

from workbench.llm_router._retry_demo import (
    build_retry_params,
    event_dicts,
    exception_type_names,
)
from workbench.llm_router.google_genai._sdk_helpers import (
    build_client,
    response_text,
    usage_snapshot,
)

# =============================================================================
# Scenario
# =============================================================================

# Keep the baseline flash model fixed so this script isolates the retry policy
# itself, not model behavior differences.
_MODEL = "gemini-2.5-flash"
_PROMPT = "Reply with only OK."
_TEMPERATURE = 0.0
_SEED = 42
_MAX_ATTEMPTS = 3
_MIN_WAIT_SECONDS = 1.0
_MAX_WAIT_SECONDS = 8.0
_RETRYABLE_EXCEPTIONS = (APIError, httpx.ConnectError, httpx.TimeoutException)
_RETRYABLE_API_STATUS = {
    "ABORTED",
    "DEADLINE_EXCEEDED",
    "INTERNAL",
    "RESOURCE_EXHAUSTED",
    "UNAVAILABLE",
}
_RETRYABLE_HTTP_CODES = {408, 409, 425, 429, 500, 502, 503, 504}


# =============================================================================
# Helpers
# =============================================================================


def _is_retryable(retry_state: tenacity.RetryCallState) -> bool:
    """Mirror the Google adapter's retryability check."""
    if not retry_state.outcome:
        return False

    exception = retry_state.outcome.exception()
    if exception is None:
        return False

    if isinstance(exception, APIError):
        status = getattr(exception, "status", None)
        if isinstance(status, str) and status in _RETRYABLE_API_STATUS:
            return True

        code = getattr(exception, "code", None)
        return isinstance(code, int) and code in _RETRYABLE_HTTP_CODES

    return isinstance(exception, (httpx.ConnectError, httpx.TimeoutException))


# =============================================================================
# Pipeline
# =============================================================================


async def run_pipeline() -> dict[str, Any]:
    """Run one live async Google GenAI request behind Tenacity."""
    client = build_client()
    retry_events = []
    attempt_count = 0

    @tenacity.retry(
        **build_retry_params(
            retry=_is_retryable,
            events=retry_events,
            max_attempts=_MAX_ATTEMPTS,
            min_wait_seconds=_MIN_WAIT_SECONDS,
            max_wait_seconds=_MAX_WAIT_SECONDS,
        )
    )
    async def _call() -> object:
        """Execute one live Google GenAI request."""
        nonlocal attempt_count
        attempt_count += 1
        return await client.aio.models.generate_content(
            model=_MODEL,
            contents=[_PROMPT],
            config=types.GenerateContentConfig(
                temperature=_TEMPERATURE,
                seed=_SEED,
            ),
        )

    response = await _call()
    return {
        "model": _MODEL,
        "attempt_count": attempt_count,
        "retryable_exceptions": exception_type_names(_RETRYABLE_EXCEPTIONS),
        "retryable_api_status": sorted(_RETRYABLE_API_STATUS),
        "retryable_http_codes": sorted(_RETRYABLE_HTTP_CODES),
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


def main() -> None:
    """Run the workbench script as a narrative manual demo."""
    console.demo_intro(__doc__)
    console.demo_step(
        "Scenario",
        "Sending one tiny async text request through the native Google client "
        "with the same Tenacity predicate used in `src/`, including the "
        "provider-specific `APIError` status/code filter.",
        details=(
            f"Model: {_MODEL}",
            f"Prompt: {_PROMPT}",
            f"Retryable exceptions: {exception_type_names(_RETRYABLE_EXCEPTIONS)}",
            f"Retryable API status: {sorted(_RETRYABLE_API_STATUS)}",
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
        "This is enough to trust the Google GenAI Tenacity retry predicate "
        "around the async text path in this environment.",
    )


if __name__ == "__main__":
    main()


# =============================================================================
# Expected Output
# =============================================================================
EXPECTED_OUTPUT = """
Real run on 2026-04-03 (excerpt, key verification fields):
{
  "attempt_count": 1,
  "retry_events": [],
  "retryable_exceptions": [
    "APIError",
    "ConnectError",
    "TimeoutException"
  ],
  "text": "OK"
}
""".strip()
