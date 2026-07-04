# %%
"""QwenChat async retry text-generation workbench script.

Why:
    Shows the Tenacity retry contract used by the direct QwenChat adapter on
    one real async text request.

Covers:
    Area: qwenchat live async retry policy
    Behavior: Tenacity retry wrapper around one async proxy completion
    Interface: `POST /chat/completions`

Checks:
    If the result exposes `retryable_exceptions`, `retryable_status_codes`, and
        `retry_policy`, then the script is probing the same retry contract used by
        `src/`.
    If the result exposes `attempt_count` and `retry_events`, then the manual run can
        show whether the live request succeeded immediately or only after retries.
    If the retried call still returns `text`, `normalized_reply`, and `usage`, then the
        retry wrapper preserved a usable successful response.

Examples:
    Run manually:
        uv run python -m workbench.llm_router.qwenchat.retry_text_generation_async
        uv run python scripts/runtime/reproduce_running_loop.py \
            workbench.llm_router.qwenchat.retry_text_generation_async
"""

from __future__ import annotations

import os
from typing import Any

import httpx
import tenacity

from tests.support.console import console
from tests.support.setup import run_async
from workbench.llm_router._retry_demo import (
    build_retry_params,
    event_dicts,
    exception_type_names,
)
from workbench.llm_router.qwenchat._chat_completions import (
    build_payload,
    response_text,
    usage_snapshot,
)
from workbench.llm_router.qwenchat._runtime import (
    api_key_env_name,
    build_async_client,
    completion_url,
    qwenchat_base_url,
)
from workbench.llm_router.qwenchat._structured_output import normalize_reply
from workbench.llm_router.qwenchat._uploads import build_user_content_async


class _RetryableProxyError(RuntimeError):
    """Mirror the adapter's retryable proxy-status branch for workbench demos."""


# =============================================================================
# Scenario
# =============================================================================

# Keep the same tiny prompt and model as the plain text probe so this script
# isolates retry behavior around the async Qwen completion route.
_MODEL = "qwen-max-latest"
_SYSTEM_PROMPT = "Follow instructions exactly. Reply with only what is asked."
_PROMPT = "Reply with only: pong"
_TEMPERATURE = 0.0
_SEED = 42
_MAX_ATTEMPTS = 3
_MIN_WAIT_SECONDS = 1.0
_MAX_WAIT_SECONDS = 8.0
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
_RETRYABLE_EXCEPTIONS = (httpx.RequestError, _RetryableProxyError)


# =============================================================================
# Helpers
# =============================================================================


def _completion_headers() -> dict[str, str]:
    """Build the completion headers used by the direct Qwen proxy."""
    api_key = os.getenv(api_key_env_name(), "").strip()
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


async def _post_completion_with_retryable_status(
    *,
    client: httpx.AsyncClient,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """POST one completion request and mirror the adapter's retryable status split."""
    response = await client.post(
        completion_url(),
        headers=_completion_headers(),
        json=payload,
    )
    if response.status_code in _RETRYABLE_STATUS_CODES:
        msg = (
            "The live QwenChat completion request returned one retryable status "
            f"{response.status_code}: {response.text}"
        )
        raise _RetryableProxyError(msg)
    if not response.is_success:
        msg = (
            "The live QwenChat completion request failed without a retryable "
            f"status: {response.status_code}: {response.text}"
        )
        raise RuntimeError(msg)
    return response.json()


# =============================================================================
# Pipeline
# =============================================================================


async def run_pipeline() -> dict[str, Any]:
    """Run one live async QwenChat request behind Tenacity."""
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
    async def _call() -> dict[str, Any]:
        """Execute one live QwenChat completion request."""
        nonlocal attempt_count
        attempt_count += 1
        async with build_async_client() as client:
            user_content = await build_user_content_async(
                client=client,
                items=[_SYSTEM_PROMPT, _PROMPT],
            )
            return await _post_completion_with_retryable_status(
                client=client,
                payload=build_payload(
                    model=_MODEL,
                    user_content=user_content,
                    temperature=_TEMPERATURE,
                    seed=_SEED,
                ),
            )

    response = await _call()
    text = response_text(response)
    return {
        "base_url": qwenchat_base_url(),
        "model": _MODEL,
        "attempt_count": attempt_count,
        "retryable_exceptions": exception_type_names(_RETRYABLE_EXCEPTIONS),
        "retryable_status_codes": sorted(_RETRYABLE_STATUS_CODES),
        "retry_policy": {
            "max_attempts": _MAX_ATTEMPTS,
            "min_wait_seconds": _MIN_WAIT_SECONDS,
            "max_wait_seconds": _MAX_WAIT_SECONDS,
        },
        "retry_events": event_dicts(retry_events),
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
        "Sending one tiny async text request through the direct QwenChat proxy "
        "with the same Tenacity exception shape used by the text adapter path "
        "in `src/`.",
        details=(
            f"Base URL: {qwenchat_base_url()}",
            f"Model: {_MODEL}",
            f"Prompt: {_PROMPT}",
            f"Retryable exceptions: {exception_type_names(_RETRYABLE_EXCEPTIONS)}",
            f"Retryable status codes: {sorted(_RETRYABLE_STATUS_CODES)}",
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
        "This is enough to trust the QwenChat Tenacity exception policy around "
        "the async text path in this environment.",
    )


if __name__ == "__main__":
    main()


# =============================================================================
# Expected Output
# =============================================================================
EXPECTED_OUTPUT = """
Real run on 2026-04-13 (excerpt, key verification fields):
{
  "attempt_count": 1,
  "normalized_reply": "pong",
  "retry_events": [],
  "retryable_exceptions": [
    "RequestError",
    "_RetryableProxyError"
  ],
  "text": "pong"
}
""".strip()
