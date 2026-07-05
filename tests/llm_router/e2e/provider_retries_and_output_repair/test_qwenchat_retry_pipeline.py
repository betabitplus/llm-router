# %%
"""LLM Router e2e: QwenChat retry behavior.

Why:
    Verifies that the public QwenChat route retries a retryable provider-proxy
    failure and does not retry a non-retryable failure.

Covers:
    Area: QwenChat client
    Behavior: tenacity retry on retryable failure, fail-fast on non-retryable failure
    Interface: `LLMRouter(RouterProfile(...))`, `query(...)`

Checks:
    If a proxy response returns a retryable `429`, then the worker succeeds with the
    retry text after exactly 2 chat-endpoint hits.
    If a proxy response returns a retryable `503`, then the worker succeeds with the
    retry text after exactly 2 chat-endpoint hits.
    If a proxy response returns a non-retryable `400`, then the worker ends in a clean
    `ProviderError` result with the scripted message after exactly 1 chat-endpoint hit.
    If a proxy response returns a non-retryable `401`, then the worker ends in a clean
    `ProviderError` result with the scripted message after exactly 1 chat-endpoint hit.
    If an upload returns a retryable `429`, then the worker succeeds with the retry text
    after exactly 2 upload hits and exactly 1 chat-completion hit.
    If an upload returns a retryable `503`, then the worker succeeds with the retry text
    after exactly 2 upload hits and exactly 1 chat-completion hit.
    If an upload returns a non-retryable `400`, then the worker ends in a clean
    `ProviderError` result with the scripted message after exactly 1 upload hit and 0
    chat-completion hits.

Notes:
    This scenario is hermetic by construction because it talks only to a local
    scripted HTTP server.

Examples:
    Run manually:
        uv run python -m \
            tests.llm_router.e2e.provider_retries_and_output_repair.test_qwenchat_retry_pipeline

    Run as test:
        pytest \
            tests/llm_router/e2e/provider_retries_and_output_repair/test_qwenchat_retry_pipeline.py
"""

from __future__ import annotations

import pytest
from py_lib_tooling import console

from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    RetryWorkerResult,
    qwen_chat_path,
    qwen_error_response,
    qwen_success_response,
    qwen_upload_path,
    qwen_upload_success_response,
    run_retry_worker,
)

pytestmark = [
    pytest.mark.e2e_behavior,
    pytest.mark.cap_resilience,
    pytest.mark.hermetic,
]


# =============================================================================
# Scenario
# =============================================================================

_PORT = 0
_PATH = qwen_chat_path()
_UPLOAD_PATH = qwen_upload_path()
_RETRY_TEXT = "qwenchat retry ok on server-attempt-2"
_NON_RETRYABLE_MESSAGE = "qwenchat bad request"
_AUTH_MESSAGE = "qwenchat unauthorized"
_UPLOAD_URL = "https://local.qwen/uploaded/image.png"
_UPLOAD_NON_RETRYABLE_MESSAGE = "qwenchat upload bad request"
_CASE = "qwenchat"


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
                body=qwen_error_response(
                    status_code=429,
                    message="retry me once",
                ),
            ),
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=qwen_success_response(text=_RETRY_TEXT),
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
                body=qwen_error_response(
                    status_code=503,
                    message="service unavailable once",
                ),
            ),
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=qwen_success_response(text=_RETRY_TEXT),
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
                body=qwen_error_response(
                    status_code=400,
                    message=_NON_RETRYABLE_MESSAGE,
                ),
            ),
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=qwen_success_response(text="unexpected retry"),
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
                body=qwen_error_response(
                    status_code=401,
                    message=_AUTH_MESSAGE,
                ),
            ),
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=qwen_success_response(text="unexpected retry"),
            ),
        ]
    }


def retryable_upload_routes() -> dict[tuple[str, str], list[ScriptedResponse]]:
    """Build scripted routes for retryable upload recovery."""
    return {
        ("POST", _UPLOAD_PATH): [
            ScriptedResponse(
                status_code=429,
                headers={"Content-Type": "application/json"},
                body=qwen_error_response(
                    status_code=429,
                    message="retry upload once",
                ),
            ),
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=qwen_upload_success_response(url=_UPLOAD_URL),
            ),
        ],
        ("POST", _PATH): [
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=qwen_success_response(text=_RETRY_TEXT),
            )
        ],
    }


def retryable_upload_server_error_routes() -> dict[
    tuple[str, str],
    list[ScriptedResponse],
]:
    """Build scripted routes for retryable upload server-error recovery."""
    return {
        ("POST", _UPLOAD_PATH): [
            ScriptedResponse(
                status_code=503,
                headers={"Content-Type": "application/json"},
                body=qwen_error_response(
                    status_code=503,
                    message="retry upload service unavailable",
                ),
            ),
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=qwen_upload_success_response(url=_UPLOAD_URL),
            ),
        ],
        ("POST", _PATH): [
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=qwen_success_response(text=_RETRY_TEXT),
            )
        ],
    }


def non_retryable_upload_routes() -> dict[tuple[str, str], list[ScriptedResponse]]:
    """Build scripted routes for a non-retryable upload failure."""
    return {
        ("POST", _UPLOAD_PATH): [
            ScriptedResponse(
                status_code=400,
                headers={"Content-Type": "application/json"},
                body=qwen_error_response(
                    status_code=400,
                    message=_UPLOAD_NON_RETRYABLE_MESSAGE,
                ),
            ),
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=qwen_upload_success_response(url=_UPLOAD_URL),
            ),
        ],
        ("POST", _PATH): [
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=qwen_success_response(text="unexpected completion"),
            )
        ],
    }


# =============================================================================
# Pipeline
# =============================================================================


def run_retry_pipeline(*, server_base_url: str) -> RetryWorkerResult:
    """Run the retryable QwenChat scenario."""
    # This worker path isolates a recoverable chat failure.
    return run_retry_worker(
        case=_CASE,
        scenario="retryable",
        server_base_url=server_base_url,
    )


def run_non_retryable_pipeline(*, server_base_url: str) -> RetryWorkerResult:
    """Run the non-retryable QwenChat scenario."""
    # This worker path isolates a permanent chat failure.
    return run_retry_worker(
        case=_CASE,
        scenario="non_retryable",
        server_base_url=server_base_url,
    )


def run_retryable_upload_pipeline(*, server_base_url: str) -> RetryWorkerResult:
    """Run the retryable Qwen upload scenario."""
    # This worker path isolates a recoverable upload failure before completion.
    return run_retry_worker(
        case=_CASE,
        scenario="retryable_upload",
        server_base_url=server_base_url,
    )


def run_non_retryable_upload_pipeline(*, server_base_url: str) -> RetryWorkerResult:
    """Run the non-retryable Qwen upload scenario."""
    # This worker path isolates a permanent upload failure before completion.
    return run_retry_worker(
        case=_CASE,
        scenario="non_retryable_upload",
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
    # The standard chat path should recover successfully on retryable failures.
    assert response.returncode == 0
    assert response.ok is True, response.stderr or response.error_message
    assert response.output_text == _RETRY_TEXT
    # Two chat hits prove that the retry path really ran.
    assert server.request_count("POST", _PATH) == 2


def assert_non_retryable_error(
    result: RetryWorkerResult,
    *,
    server: ScriptedHTTPServer,
    expected_message: str,
) -> None:
    """Assert the non-retryable public error."""
    # The worker should report a clean failure result.
    assert result.returncode == 0
    assert result.ok is False
    assert result.error_type == "ProviderError"
    assert expected_message in (result.error_message or "")
    # One chat hit proves fail-fast behavior on permanent failures.
    assert server.request_count("POST", _PATH) == 1


def assert_retryable_upload_response(
    response: RetryWorkerResult,
    *,
    server: ScriptedHTTPServer,
) -> None:
    """Assert the retryable upload recovery response."""
    # Upload recovery should still end in one successful final chat response.
    assert response.returncode == 0
    assert response.ok is True, response.stderr or response.error_message
    assert response.output_text == _RETRY_TEXT
    # The upload endpoint should show one failure and one retry success.
    assert server.request_count("POST", _UPLOAD_PATH) == 2
    # The chat endpoint should be called once only after upload recovery.
    assert server.request_count("POST", _PATH) == 1


def assert_non_retryable_upload_error(
    result: RetryWorkerResult,
    *,
    server: ScriptedHTTPServer,
) -> None:
    """Assert the non-retryable upload public error."""
    # A permanent upload failure should surface as a provider error.
    assert result.returncode == 0
    assert result.ok is False
    assert result.error_type == "ProviderError"
    assert _UPLOAD_NON_RETRYABLE_MESSAGE in (result.error_message or "")
    # One upload hit and zero chat hits prove the flow stopped before any model
    # completion attempt was made.
    assert server.request_count("POST", _UPLOAD_PATH) == 1
    assert server.request_count("POST", _PATH) == 0


# =============================================================================
# Tests
# =============================================================================


def test_retryable_failure_retries_then_succeeds() -> None:
    """Verify retryable Qwen proxy failures are retried."""
    with ScriptedHTTPServer(port=_PORT, routes=retryable_routes()) as server:
        # First run the recoverable chat failure path.
        response = run_retry_pipeline(server_base_url=server.base_url)
        # Then prove the visible answer came from the retried success.
        assert_retry_response(response, server=server)


def test_retryable_server_error_retries_then_succeeds() -> None:
    """Verify retryable Qwen proxy server errors are retried."""
    with ScriptedHTTPServer(
        port=_PORT,
        routes=retryable_server_error_routes(),
    ) as server:
        response = run_retry_pipeline(server_base_url=server.base_url)
        assert_retry_response(response, server=server)


def test_non_retryable_failure_does_not_retry() -> None:
    """Verify non-retryable Qwen proxy failures do not retry."""
    with ScriptedHTTPServer(port=_PORT, routes=non_retryable_routes()) as server:
        # Run the permanent chat-failure path once.
        result = run_non_retryable_pipeline(server_base_url=server.base_url)
        # Then prove the router stopped immediately.
        assert_non_retryable_error(
            result,
            server=server,
            expected_message=_NON_RETRYABLE_MESSAGE,
        )


def test_non_retryable_auth_failure_does_not_retry() -> None:
    """Verify non-retryable Qwen auth failures do not retry."""
    with ScriptedHTTPServer(port=_PORT, routes=non_retryable_auth_routes()) as server:
        result = run_non_retryable_pipeline(server_base_url=server.base_url)
        assert_non_retryable_error(
            result,
            server=server,
            expected_message=_AUTH_MESSAGE,
        )


def test_retryable_upload_failure_retries_then_succeeds() -> None:
    """Verify retryable Qwen upload failures are retried."""
    with ScriptedHTTPServer(port=_PORT, routes=retryable_upload_routes()) as server:
        # Here the recoverable failure happens before any chat completion call.
        response = run_retryable_upload_pipeline(server_base_url=server.base_url)
        assert_retryable_upload_response(response, server=server)


def test_retryable_upload_server_error_retries_then_succeeds() -> None:
    """Verify retryable Qwen upload server errors are retried."""
    with ScriptedHTTPServer(
        port=_PORT,
        routes=retryable_upload_server_error_routes(),
    ) as server:
        response = run_retryable_upload_pipeline(server_base_url=server.base_url)
        assert_retryable_upload_response(response, server=server)


def test_non_retryable_upload_failure_does_not_retry() -> None:
    """Verify non-retryable Qwen upload failures do not retry."""
    with ScriptedHTTPServer(port=_PORT, routes=non_retryable_upload_routes()) as server:
        result = run_non_retryable_upload_pipeline(server_base_url=server.base_url)
        assert_non_retryable_upload_error(result, server=server)


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the retry demo flow for manual execution."""
    console.demo_intro(__doc__)
    with ScriptedHTTPServer(port=_PORT, routes=retryable_routes()) as server:
        response = run_retry_pipeline(server_base_url=server.base_url)
        assert_retry_response(response, server=server)

        console.demo_step(
            "What Happened On The Completion Recovery Path",
            "The completion request retried once and then succeeded.",
            details=[
                f"Final output: {response.output_text}",
                f"Chat hits: {server.request_count('POST', _PATH)}",
            ],
        )

    with ScriptedHTTPServer(port=_PORT, routes=non_retryable_routes()) as server:
        result = run_non_retryable_pipeline(server_base_url=server.base_url)
        assert_non_retryable_error(
            result,
            server=server,
            expected_message=_NON_RETRYABLE_MESSAGE,
        )

        console.demo_step(
            "What Happened On The Completion Fail-Fast Path",
            "A non-retryable completion error was surfaced immediately.",
            details=[
                f"Public error: {result.error_type}: {result.error_message}",
                f"Chat hits: {server.request_count('POST', _PATH)}",
            ],
        )

    with ScriptedHTTPServer(port=_PORT, routes=retryable_upload_routes()) as server:
        upload_response = run_retryable_upload_pipeline(server_base_url=server.base_url)
        assert_retryable_upload_response(upload_response, server=server)

        console.demo_step(
            "What Happened On The Upload Recovery Path",
            "The upload recovered first, and only then did the final "
            "completion run successfully.",
            details=[
                f"Final output: {upload_response.output_text}",
                f"Upload hits: {server.request_count('POST', _UPLOAD_PATH)}",
                f"Chat hits: {server.request_count('POST', _PATH)}",
            ],
        )

    with ScriptedHTTPServer(port=_PORT, routes=non_retryable_upload_routes()) as server:
        upload_error = run_non_retryable_upload_pipeline(
            server_base_url=server.base_url
        )
        assert_non_retryable_upload_error(upload_error, server=server)

        console.demo_step(
            "What Happened On The Upload Fail-Fast Path",
            "A non-retryable upload error stopped the flow before the "
            "completion request was even attempted.",
            details=[
                "Public error: "
                f"{upload_error.error_type}: {upload_error.error_message}",
                f"Upload hits: {server.request_count('POST', _UPLOAD_PATH)}",
                f"Chat hits: {server.request_count('POST', _PATH)}",
            ],
        )
    console.demo_outcome(
        "This passed because both the upload phase and the completion "
        "phase obeyed the same retry contract instead of behaving "
        "inconsistently."
    )


if __name__ == "__main__":
    main()
# %%
