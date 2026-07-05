# %%
"""LLM Router e2e: Gemini WebAPI retry behavior.

Why:
    Verifies that the public Gemini WebAPI route retries a retryable web-backend
    failure and does not retry a non-retryable failure.

Covers:
    Area: Gemini WebAPI client
    Behavior: tenacity retry on retryable failure, fail-fast on non-retryable failure
    Interface: `LLMRouter(RouterProfile(...))`, `query(...)`

Checks:
    If the browser-backed transport timeout is retryable, then the worker succeeds with
    the retry text after exactly 2 batch hits and 2 generate hits.
    If the browser-backed provider API error is retryable, then the worker succeeds with
    the retry text after exactly 2 batch hits and 2 generate hits.
    If the Gemini server error is non-retryable, then the worker ends in a clean
    `ProviderError` result with the scripted message after exactly 1 batch hit and 1
    generate hit.

Notes:
    This scenario is hermetic by construction because it talks only to a local
    scripted HTTP server and patches only external SDK modules in an isolated
    subprocess rather than changing library code.

Examples:
    Run manually:
        uv run python -m \
            tests.llm_router.e2e.provider_retries_and_output_repair.test_gemini_webapi_retry_pipeline

    Run as test:
        pytest \
            tests/llm_router/e2e/provider_retries_and_output_repair/test_gemini_webapi_retry_pipeline.py
"""

from __future__ import annotations

import pytest

from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    RetryWorkerResult,
    gemini_webapi_batch_path,
    gemini_webapi_batch_response,
    gemini_webapi_error_stream_response,
    gemini_webapi_generate_path,
    gemini_webapi_google_path,
    gemini_webapi_init_path,
    gemini_webapi_init_response,
    gemini_webapi_stream_response,
    run_retry_worker,
)
from py_lib_tooling import console

pytestmark = [
    pytest.mark.e2e_behavior,
    pytest.mark.cap_resilience,
    pytest.mark.hermetic,
]


# =============================================================================
# Scenario
# =============================================================================

_PORT = 0
_GOOGLE_PATH = gemini_webapi_google_path()
_INIT_PATH = gemini_webapi_init_path()
_BATCH_PATH = gemini_webapi_batch_path()
_GENERATE_PATH = gemini_webapi_generate_path()
_RETRY_TEXT = "gemini-webapi retry ok on server-attempt-2"
_TIMEOUT_DELAY_SECONDS = 0.2
_NON_RETRYABLE_MESSAGE = "temporarily flagged or blocked"
_CASE = "gemini_webapi"


# =============================================================================
# Helpers
# =============================================================================


def _bootstrap_routes() -> dict[tuple[str, str], list[ScriptedResponse]]:
    """Build shared bootstrap routes required by gemini_webapi."""
    return {
        ("GET", _GOOGLE_PATH): [
            ScriptedResponse(status_code=200, body=b"ok"),
        ],
        ("GET", _INIT_PATH): [
            ScriptedResponse(status_code=200, body=gemini_webapi_init_response()),
        ],
        ("POST", _BATCH_PATH): [
            ScriptedResponse(status_code=200, body=gemini_webapi_batch_response()),
        ],
    }


def retryable_routes() -> dict[tuple[str, str], list[ScriptedResponse]]:
    """Build scripted routes for retryable-failure recovery."""
    return {
        **_bootstrap_routes(),
        ("POST", _GENERATE_PATH): [
            ScriptedResponse(
                status_code=200,
                body=gemini_webapi_stream_response(text=_RETRY_TEXT),
                delay_seconds=_TIMEOUT_DELAY_SECONDS,
            ),
            ScriptedResponse(
                status_code=200,
                body=gemini_webapi_stream_response(text=_RETRY_TEXT),
            ),
        ],
    }


def non_retryable_routes() -> dict[tuple[str, str], list[ScriptedResponse]]:
    """Build scripted routes for a non-retryable failure."""
    return {
        **_bootstrap_routes(),
        ("POST", _GENERATE_PATH): [
            ScriptedResponse(
                status_code=200,
                body=gemini_webapi_error_stream_response(error_code=1060),
            ),
        ],
    }


def retryable_api_error_routes() -> dict[tuple[str, str], list[ScriptedResponse]]:
    """Build scripted routes for a retryable provider API error."""
    return {
        **_bootstrap_routes(),
        ("POST", _GENERATE_PATH): [
            ScriptedResponse(status_code=500, body=b"temporary server error"),
            ScriptedResponse(
                status_code=200,
                body=gemini_webapi_stream_response(text=_RETRY_TEXT),
            ),
        ],
    }


# =============================================================================
# Pipeline
# =============================================================================


def run_retry_pipeline(*, server_base_url: str) -> RetryWorkerResult:
    """Run the retryable Gemini WebAPI scenario."""
    # This worker path isolates a retryable timeout on the browser-backed flow.
    return run_retry_worker(
        case=_CASE,
        scenario="retryable",
        server_base_url=server_base_url,
    )


def run_non_retryable_pipeline(*, server_base_url: str) -> RetryWorkerResult:
    """Run the non-retryable Gemini WebAPI scenario."""
    # This worker path isolates a permanent backend error.
    return run_retry_worker(
        case=_CASE,
        scenario="non_retryable",
        server_base_url=server_base_url,
    )


def run_retryable_api_error_pipeline(*, server_base_url: str) -> RetryWorkerResult:
    """Run the retryable Gemini WebAPI API-error scenario."""
    # This worker path isolates a retryable server-side API error.
    return run_retry_worker(
        case=_CASE,
        scenario="retryable_api_error",
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
    # The browser-backed route should still end in success for retryable cases.
    assert response.returncode == 0
    assert response.ok is True, response.stderr or response.error_message
    # The visible answer proves the generate step eventually recovered.
    assert response.output_text == _RETRY_TEXT
    # Gemini WebAPI has both batch and generate steps, so both counts should
    # show two hits when one retry happened.
    assert server.request_count("POST", _BATCH_PATH) == 2
    assert server.request_count("POST", _GENERATE_PATH) == 2


def assert_non_retryable_error(
    result: RetryWorkerResult,
    *,
    server: ScriptedHTTPServer,
) -> None:
    """Assert the non-retryable public error."""
    # The worker completes, but the router should surface a failure outcome.
    assert result.returncode == 0
    assert result.ok is False
    # The error must stay a provider error with the specific non-retryable message.
    assert result.error_type == "ProviderError"
    assert _NON_RETRYABLE_MESSAGE in (result.error_message or "")
    # One batch and one generate hit prove the route did not retry.
    assert server.request_count("POST", _BATCH_PATH) == 1
    assert server.request_count("POST", _GENERATE_PATH) == 1


# =============================================================================
# Tests
# =============================================================================


def test_retryable_failure_retries_then_succeeds() -> None:
    """Verify retryable Gemini WebAPI failures are retried."""
    with ScriptedHTTPServer(port=_PORT, routes=retryable_routes()) as server:
        # First run the recoverable timeout path.
        response = run_retry_pipeline(server_base_url=server.base_url)
        # Then prove both batch and generate stages retried exactly once.
        assert_retry_response(response, server=server)


def test_non_retryable_failure_does_not_retry() -> None:
    """Verify non-retryable Gemini WebAPI failures do not retry."""
    with ScriptedHTTPServer(port=_PORT, routes=non_retryable_routes()) as server:
        # Run the permanent-failure path once.
        result = run_non_retryable_pipeline(server_base_url=server.base_url)
        # Then prove the route stopped immediately.
        assert_non_retryable_error(result, server=server)


def test_retryable_api_error_retries_then_succeeds() -> None:
    """Verify retryable Gemini WebAPI API errors are retried exactly once."""
    with ScriptedHTTPServer(port=_PORT, routes=retryable_api_error_routes()) as server:
        # Repeat the recovery proof for a backend API error instead of a timeout.
        response = run_retryable_api_error_pipeline(server_base_url=server.base_url)
        assert_retry_response(response, server=server)


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the retry demo flow for manual execution."""
    console.demo_intro(__doc__)
    with ScriptedHTTPServer(port=_PORT, routes=retryable_routes()) as server:
        # Show timeout recovery first.
        timeout_response = run_retry_pipeline(server_base_url=server.base_url)
        assert_retry_response(timeout_response, server=server)

        console.demo_step(
            "What Happened On The Timeout Recovery Path",
            "The web-backed path recovered after a timeout and then "
            "completed successfully.",
            details=[
                f"Final output: {timeout_response.output_text}",
                f"Batch hits: {server.request_count('POST', _BATCH_PATH)}",
                f"Generate hits: {server.request_count('POST', _GENERATE_PATH)}",
            ],
        )

    with ScriptedHTTPServer(port=_PORT, routes=retryable_api_error_routes()) as server:
        # Then show that API-error recovery follows the same rule.
        api_error_response = run_retryable_api_error_pipeline(
            server_base_url=server.base_url
        )
        assert_retry_response(api_error_response, server=server)

        console.demo_step(
            "What Happened On The API-Error Recovery Path",
            "A retryable backend error also recovered on the next attempt.",
            details=[
                f"Final output: {api_error_response.output_text}",
                f"Batch hits: {server.request_count('POST', _BATCH_PATH)}",
                f"Generate hits: {server.request_count('POST', _GENERATE_PATH)}",
            ],
        )

    with ScriptedHTTPServer(port=_PORT, routes=non_retryable_routes()) as server:
        # Finally, contrast recovery with the fail-fast branch.
        non_retryable = run_non_retryable_pipeline(server_base_url=server.base_url)
        assert_non_retryable_error(non_retryable, server=server)

        console.demo_step(
            "What Happened On The Fail-Fast Path",
            "A non-retryable backend error was surfaced to the caller immediately.",
            details=[
                "Public error: "
                f"{non_retryable.error_type}: {non_retryable.error_message}",
                f"Batch hits: {server.request_count('POST', _BATCH_PATH)}",
                f"Generate hits: {server.request_count('POST', _GENERATE_PATH)}",
            ],
        )
    console.demo_outcome(
        "This passed because the browser-backed route behaved "
        "predictably across recovery and fail-fast cases instead of "
        "hiding what happened."
    )


if __name__ == "__main__":
    main()
# %%
