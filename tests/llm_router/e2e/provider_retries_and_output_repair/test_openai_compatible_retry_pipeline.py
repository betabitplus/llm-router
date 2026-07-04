# %%
"""LLM Router e2e: OpenAI-compatible retry behavior.

Why:
    Verifies that the public OpenAI-compatible route retries a retryable
    provider failure and does not retry a non-retryable failure.

Covers:
    Area: OpenAI-compatible client family
    Behavior: tenacity retry on retryable failure, fail-fast on non-retryable failure
    Interface: `LLMRouter(RouterProfile(...))`, `query(...)`

Checks:
    If a `429` response is retryable, then the worker succeeds with the retry text after
    exactly 2 provider hits.
    If a `503` response is retryable, then the worker succeeds with the retry text after
    exactly 2 provider hits.
    If a connection interruption is retryable, then the worker succeeds with the retry
    text after exactly 2 provider hits.
    If a `400` response is non-retryable, then the worker ends in a clean
    `ProviderError` result with the scripted message after exactly 1 provider hit.
    If a `401` response is non-retryable, then the worker ends in a clean
    `ProviderError` result with the scripted message after exactly 1 provider hit.

Notes:
    This scenario is hermetic by construction because it talks only to a local
    scripted HTTP server.

Examples:
    Run manually:
        uv run python -m \
            tests.llm_router.e2e.provider_retries_and_output_repair.test_openai_compatible_retry_pipeline

    Run as test:
        pytest \
            tests/llm_router/e2e/provider_retries_and_output_repair/test_openai_compatible_retry_pipeline.py
"""

from __future__ import annotations

import pytest

from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    RetryWorkerResult,
    openai_chat_path,
    openai_error_response,
    openai_success_response,
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
_PATH = openai_chat_path()
_RETRY_TEXT = "openai-compatible retry ok on server-attempt-2"
_NON_RETRYABLE_MESSAGE = "openai-compatible bad request"
_AUTH_MESSAGE = "openai-compatible unauthorized"
_CASE = "openai"


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
                body=openai_error_response(
                    status_code=429,
                    message="retry me once",
                ),
            ),
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=openai_success_response(text=_RETRY_TEXT),
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
                body=openai_error_response(
                    status_code=503,
                    message="service unavailable once",
                ),
            ),
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=openai_success_response(text=_RETRY_TEXT),
            ),
        ]
    }


def retryable_disconnect_routes() -> dict[tuple[str, str], list[ScriptedResponse]]:
    """Build scripted routes for retryable connection-interruption recovery."""
    return {
        ("POST", _PATH): [
            ScriptedResponse(status_code=0, disconnect=True),
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=openai_success_response(text=_RETRY_TEXT),
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
                body=openai_error_response(
                    status_code=400,
                    message=_NON_RETRYABLE_MESSAGE,
                ),
            ),
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=openai_success_response(text="unexpected retry"),
            ),
        ]
    }


def non_retryable_auth_routes() -> dict[tuple[str, str], list[ScriptedResponse]]:
    """Build scripted routes for a non-retryable auth failure."""
    return {
        ("POST", _PATH): [
            ScriptedResponse(
                status_code=401,
                headers={"Content-Type": "application/json"},
                body=openai_error_response(
                    status_code=401,
                    message=_AUTH_MESSAGE,
                ),
            ),
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=openai_success_response(text="unexpected retry"),
            ),
        ]
    }


# =============================================================================
# Pipeline
# =============================================================================


def run_retry_pipeline(*, server_base_url: str) -> RetryWorkerResult:
    """Run the retryable OpenAI-compatible scenario."""
    # This worker path isolates one recoverable provider failure.
    return run_retry_worker(
        case=_CASE,
        scenario="retryable",
        server_base_url=server_base_url,
    )


def run_non_retryable_pipeline(*, server_base_url: str) -> RetryWorkerResult:
    """Run the non-retryable OpenAI-compatible scenario."""
    # This worker path isolates one permanent provider failure.
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
    # The whole scenario should end in success after one retryable failure.
    assert response.returncode == 0
    assert response.ok is True, response.stderr or response.error_message
    # The final visible output must come from the successful retry attempt.
    assert response.output_text == _RETRY_TEXT
    # Two provider hits prove that the retry path was actually exercised.
    assert server.request_count("POST", _PATH) == 2


def assert_non_retryable_error(
    result: RetryWorkerResult,
    *,
    server: ScriptedHTTPServer,
    expected_message: str,
) -> None:
    """Assert the non-retryable public error."""
    # The worker itself must still complete normally.
    assert result.returncode == 0
    assert result.ok is False
    # The public error type must stay specific to a provider failure.
    assert result.error_type == "ProviderError"
    assert expected_message in (result.error_message or "")
    # One hit is the proof that non-retryable failures fail fast.
    assert server.request_count("POST", _PATH) == 1


# =============================================================================
# Tests
# =============================================================================


def test_retryable_failure_retries_then_succeeds() -> None:
    """Verify retryable OpenAI-compatible failures are retried."""
    with ScriptedHTTPServer(port=_PORT, routes=retryable_routes()) as server:
        # First run the recoverable failure path.
        response = run_retry_pipeline(server_base_url=server.base_url)
        # Then prove the second attempt was the visible success.
        assert_retry_response(response, server=server)


def test_retryable_server_error_retries_then_succeeds() -> None:
    """Verify retryable OpenAI-compatible server errors are retried."""
    with ScriptedHTTPServer(
        port=_PORT,
        routes=retryable_server_error_routes(),
    ) as server:
        # Repeat the same proof for a retryable 5xx response.
        response = run_retry_pipeline(server_base_url=server.base_url)
        assert_retry_response(response, server=server)


def test_retryable_disconnect_retries_then_succeeds() -> None:
    """Verify retryable OpenAI-compatible disconnects are retried."""
    with ScriptedHTTPServer(port=_PORT, routes=retryable_disconnect_routes()) as server:
        # Here the first failure is a disconnect instead of an HTTP error.
        response = run_retry_pipeline(server_base_url=server.base_url)
        assert_retry_response(response, server=server)


def test_non_retryable_failure_does_not_retry() -> None:
    """Verify non-retryable OpenAI-compatible failures do not retry."""
    with ScriptedHTTPServer(port=_PORT, routes=non_retryable_routes()) as server:
        # Run the permanent-failure path once.
        result = run_non_retryable_pipeline(server_base_url=server.base_url)
        # Then prove the router stopped immediately.
        assert_non_retryable_error(
            result,
            server=server,
            expected_message=_NON_RETRYABLE_MESSAGE,
        )


def test_non_retryable_auth_failure_does_not_retry() -> None:
    """Verify non-retryable OpenAI-compatible auth failures do not retry."""
    with ScriptedHTTPServer(port=_PORT, routes=non_retryable_auth_routes()) as server:
        # Repeat the fail-fast proof for an auth-style error.
        result = run_non_retryable_pipeline(server_base_url=server.base_url)
        assert_non_retryable_error(
            result,
            server=server,
            expected_message=_AUTH_MESSAGE,
        )


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the retry demo flow for manual execution."""
    console.demo_intro(__doc__)
    with ScriptedHTTPServer(port=_PORT, routes=retryable_routes()) as server:
        # Show the recovery branch first so the optimistic path is obvious.
        response = run_retry_pipeline(server_base_url=server.base_url)
        assert_retry_response(response, server=server)

        console.demo_step(
            "What Happened On The Recovery Path",
            "The OpenAI-compatible route retried once and then succeeded.",
            details=[
                f"Final output: {response.output_text}",
                f"Server hits: {server.request_count('POST', _PATH)}",
            ],
        )

    with ScriptedHTTPServer(port=_PORT, routes=non_retryable_routes()) as server:
        # Then contrast it with the path that must not retry.
        result = run_non_retryable_pipeline(server_base_url=server.base_url)
        assert_non_retryable_error(
            result,
            server=server,
            expected_message=_NON_RETRYABLE_MESSAGE,
        )

        console.demo_step(
            "What Happened On The Fail-Fast Path",
            "A non-retryable provider error was surfaced without an unnecessary retry.",
            details=[
                f"Public error: {result.error_type}: {result.error_message}",
                f"Server hits: {server.request_count('POST', _PATH)}",
            ],
        )
    console.demo_outcome(
        "This passed because the OpenAI-compatible route recovered "
        "only when it should and stayed explicit when it should "
        "not retry."
    )


if __name__ == "__main__":
    main()
# %%
