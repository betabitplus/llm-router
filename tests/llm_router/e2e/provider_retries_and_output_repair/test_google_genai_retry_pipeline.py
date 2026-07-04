# %%
"""LLM Router e2e: Google GenAI retry behavior.

Why:
    Verifies that the public native Google route retries a retryable provider
    failure and does not retry a non-retryable failure.

Covers:
    Area: Google GenAI client
    Behavior: tenacity retry on retryable failure, fail-fast on non-retryable failure
    Interface: `LLMRouter(RouterProfile(...))`, `query(...)`

Checks:
    If a `429` response is retryable, then the worker succeeds with the retry text after
    exactly 2 provider hits.
    If a `503` response is retryable, then the worker succeeds with the retry text after
    exactly 2 provider hits.
    If a `400` response is non-retryable, then the worker ends in a clean
    `ProviderError` result with the scripted message after exactly 1 provider hit.
    If a `403` response is non-retryable, then the worker ends in a clean
    `ProviderError` result with the scripted message after exactly 1 provider hit.

Notes:
    This scenario is hermetic by construction because it talks only to a local
    scripted HTTP server.

Examples:
    Run manually:
        uv run python -m \
            tests.llm_router.e2e.provider_retries_and_output_repair.test_google_genai_retry_pipeline

    Run as test:
        pytest \
            tests/llm_router/e2e/provider_retries_and_output_repair/test_google_genai_retry_pipeline.py
"""

from __future__ import annotations

import pytest

from llm_router import Model
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    RetryWorkerResult,
    google_error_response,
    google_generate_path,
    google_success_response,
    run_retry_worker,
)
from tests.support.console import console

pytestmark = [
    pytest.mark.e2e_behavior,
    pytest.mark.cap_resilience,
    pytest.mark.hermetic,
]


# =============================================================================
# Scenario
# =============================================================================

_PORT = 0
_MODEL = Model.GEMINI_3_FLASH
_PATH = google_generate_path(model=_MODEL)
_RETRY_TEXT = "google-genai retry ok on server-attempt-2"
_NON_RETRYABLE_MESSAGE = "google-genai bad request"
_PERMISSION_MESSAGE = "google-genai permission denied"
_CASE = "google"


# =============================================================================
# Helpers
# =============================================================================


def retryable_routes() -> dict[tuple[str, str], list[ScriptedResponse]]:
    """Build scripted routes for retryable-failure recovery."""
    return {
        ("POST", _PATH): [
            ScriptedResponse(
                status_code=429,
                headers={"Content-Type": "application/json"},
                body=google_error_response(
                    status_code=429,
                    message="retry me once",
                ),
            ),
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=google_success_response(text=_RETRY_TEXT),
            ),
        ]
    }


def retryable_server_error_routes() -> dict[tuple[str, str], list[ScriptedResponse]]:
    """Build scripted routes for retryable server-error recovery."""
    return {
        ("POST", _PATH): [
            ScriptedResponse(
                status_code=503,
                headers={"Content-Type": "application/json"},
                body=google_error_response(
                    status_code=503,
                    message="service unavailable once",
                ),
            ),
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=google_success_response(text=_RETRY_TEXT),
            ),
        ]
    }


def non_retryable_routes() -> dict[tuple[str, str], list[ScriptedResponse]]:
    """Build scripted routes for a non-retryable failure."""
    return {
        ("POST", _PATH): [
            ScriptedResponse(
                status_code=400,
                headers={"Content-Type": "application/json"},
                body=google_error_response(
                    status_code=400,
                    message=_NON_RETRYABLE_MESSAGE,
                ),
            ),
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=google_success_response(text="unexpected retry"),
            ),
        ]
    }


def non_retryable_permission_routes() -> dict[tuple[str, str], list[ScriptedResponse]]:
    """Build scripted routes for a non-retryable permission failure."""
    return {
        ("POST", _PATH): [
            ScriptedResponse(
                status_code=403,
                headers={"Content-Type": "application/json"},
                body=google_error_response(
                    status_code=403,
                    message=_PERMISSION_MESSAGE,
                ),
            ),
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=google_success_response(text="unexpected retry"),
            ),
        ]
    }


# =============================================================================
# Pipeline
# =============================================================================


def run_retry_pipeline(*, server_base_url: str) -> RetryWorkerResult:
    """Run the retryable Google GenAI scenario."""
    # This worker path isolates one recoverable Google failure.
    return run_retry_worker(
        case=_CASE,
        scenario="retryable",
        server_base_url=server_base_url,
    )


def run_non_retryable_pipeline(*, server_base_url: str) -> RetryWorkerResult:
    """Run the non-retryable Google GenAI scenario."""
    # This worker path isolates one permanent Google failure.
    return run_retry_worker(
        case=_CASE,
        scenario="non_retryable",
        server_base_url=server_base_url,
    )


# =============================================================================
# Assertions
# =============================================================================


def assert_retry_response(
    response: RetryWorkerResult,
    *,
    server: ScriptedHTTPServer,
) -> None:
    """Assert the retryable-failure recovery response."""
    # The worker should succeed overall because this scenario is about recovery.
    assert response.returncode == 0
    assert response.ok is True, response.stderr or response.error_message
    # The visible answer must be the success payload from the second attempt.
    assert response.output_text == _RETRY_TEXT
    # Two hits prove that one retryable failure was followed by one successful retry.
    assert server.request_count("POST", _PATH) == 2


def assert_non_retryable_error(
    result: RetryWorkerResult,
    *,
    server: ScriptedHTTPServer,
    expected_message: str,
) -> None:
    """Assert the non-retryable public error."""
    # The worker should finish cleanly while reporting the router-level failure.
    assert result.returncode == 0
    assert result.ok is False
    # Non-retryable cases must cross the public boundary as provider errors.
    assert result.error_type == "ProviderError"
    assert expected_message in (result.error_message or "")
    # One hit proves we did not retry a permanent failure.
    assert server.request_count("POST", _PATH) == 1


# =============================================================================
# Tests
# =============================================================================


def test_retryable_failure_retries_then_succeeds() -> None:
    """Verify retryable Google failures are retried."""
    with ScriptedHTTPServer(port=_PORT, routes=retryable_routes()) as server:
        # First run the recoverable failure path.
        response = run_retry_pipeline(server_base_url=server.base_url)
        # Then prove the second attempt produced the visible success.
        assert_retry_response(response, server=server)


def test_retryable_server_error_retries_then_succeeds() -> None:
    """Verify retryable Google server errors are retried."""
    with ScriptedHTTPServer(
        port=_PORT,
        routes=retryable_server_error_routes(),
    ) as server:
        # Repeat the same recovery proof for a retryable 5xx response.
        response = run_retry_pipeline(server_base_url=server.base_url)
        assert_retry_response(response, server=server)


def test_non_retryable_failure_does_not_retry() -> None:
    """Verify non-retryable Google failures do not retry."""
    with ScriptedHTTPServer(port=_PORT, routes=non_retryable_routes()) as server:
        # Run the permanent-failure path once.
        result = run_non_retryable_pipeline(server_base_url=server.base_url)
        # Then prove the router stopped immediately.
        assert_non_retryable_error(
            result,
            server=server,
            expected_message=_NON_RETRYABLE_MESSAGE,
        )


def test_non_retryable_permission_failure_does_not_retry() -> None:
    """Verify non-retryable Google permission failures do not retry."""
    with ScriptedHTTPServer(
        port=_PORT,
        routes=non_retryable_permission_routes(),
    ) as server:
        # Repeat the fail-fast proof for a permission-style error.
        result = run_non_retryable_pipeline(server_base_url=server.base_url)
        assert_non_retryable_error(
            result,
            server=server,
            expected_message=_PERMISSION_MESSAGE,
        )


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the retry demo flow for manual execution."""
    console.demo_intro(__doc__)
    with ScriptedHTTPServer(port=_PORT, routes=retryable_routes()) as server:
        # Show the recoverable path first.
        response = run_retry_pipeline(server_base_url=server.base_url)
        assert_retry_response(response, server=server)

        console.demo_step(
            "What Happened On The Recovery Path",
            "The native Google route retried once and then succeeded.",
            details=[
                f"Final output: {response.output_text}",
                f"Server hits: {server.request_count('POST', _PATH)}",
            ],
        )

    with ScriptedHTTPServer(port=_PORT, routes=non_retryable_routes()) as server:
        # Then contrast it with the path that should fail immediately.
        result = run_non_retryable_pipeline(server_base_url=server.base_url)
        assert_non_retryable_error(
            result,
            server=server,
            expected_message=_NON_RETRYABLE_MESSAGE,
        )

        console.demo_step(
            "What Happened On The Fail-Fast Path",
            "A non-retryable Google error was surfaced immediately.",
            details=[
                f"Public error: {result.error_type}: {result.error_message}",
                f"Server hits: {server.request_count('POST', _PATH)}",
            ],
        )
    console.demo_outcome(
        "This passed because the native Google path cleanly separates "
        "retryable failures from failures that should stop at once."
    )


if __name__ == "__main__":
    main()
# %%
