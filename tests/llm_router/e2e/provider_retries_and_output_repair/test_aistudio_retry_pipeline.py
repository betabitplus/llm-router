# %%
"""LLM Router e2e: AI Studio retry behavior.

Why:
    Verifies that the public AI Studio client retries retryable failures on
    both its OpenAI-compatible path and its native Gemini video path.

Covers:
    Area: AI Studio client
    Behavior: retry on retryable failures, fail-fast on non-retryable failures
    Interface: `LLMRouter(RouterProfile(...))`, `query(...)`

Checks:
    If the non-video path receives a retryable `429`, then the worker succeeds with the
    retry text after exactly 2 non-video endpoint hits.
    If the non-video path receives a retryable `503`, then the worker succeeds with the
    retry text after exactly 2 non-video endpoint hits.
    If the non-video path receives a non-retryable `400`, then the worker ends in a
    clean `ProviderError` result with the scripted message after exactly 1 non-video
    endpoint hit.
    If the non-video path receives a non-retryable `401`, then the worker ends in a
    clean `ProviderError` result with the scripted message after exactly 1 non-video
    endpoint hit.
    If the native video path receives a retryable `429`, then the worker succeeds with
    the expected structured `VideoRetryReport` after exactly 2 video endpoint hits.
    If the native video path receives a retryable `503`, then the worker succeeds with
    the expected structured `VideoRetryReport` after exactly 2 video endpoint hits.
    If the native video path receives a non-retryable `400`, then the worker ends in a
    clean `ProviderError` result with the scripted message after exactly 1 video
    endpoint hit.
    If the native video path receives a non-retryable `401`, then the worker ends in a
    clean `ProviderError` result with the scripted message after exactly 1 video
    endpoint hit.

Notes:
    This scenario is hermetic by construction because it talks only to a local
    scripted HTTP server.

Examples:
    Run manually:
        uv run python -m \
            tests.llm_router.e2e.provider_retries_and_output_repair.test_aistudio_retry_pipeline

    Run as test:
        pytest \
            tests/llm_router/e2e/provider_retries_and_output_repair/test_aistudio_retry_pipeline.py
"""

from __future__ import annotations

import json

import pytest
from pydantic import BaseModel

from llm_router import Model
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    RetryWorkerResult,
    aistudio_stream_response,
    aistudio_video_path,
    openai_chat_path,
    openai_error_response,
    openai_success_response,
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
_NON_VIDEO_PATH = openai_chat_path()
_VIDEO_PATH = aistudio_video_path(model=Model.GEMINI_3_FLASH)
_NON_VIDEO_RETRY_TEXT = "aistudio non-video retry ok on server-attempt-2"
_VIDEO_RETRY_JSON = {"status": "retry-ok", "server_attempts": 2}
_NON_VIDEO_NON_RETRYABLE_MESSAGE = "aistudio non-video bad request"
_NON_VIDEO_AUTH_MESSAGE = "aistudio non-video unauthorized"
_VIDEO_NON_RETRYABLE_MESSAGE = "aistudio video bad request"
_VIDEO_AUTH_MESSAGE = "aistudio video unauthorized"
_NON_VIDEO_CASE = "aistudio_nonvideo"
_VIDEO_CASE = "aistudio_video"


# =============================================================================
# Helpers
# =============================================================================


class VideoRetryReport(BaseModel):
    """Structured output for the native AI Studio video retry path."""

    status: str
    server_attempts: int


def non_video_retryable_routes() -> dict[tuple[str, str], list[ScriptedResponse]]:
    """Build scripted routes for non-video retry recovery."""
    return {
        ("POST", _NON_VIDEO_PATH): [
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
                body=openai_success_response(text=_NON_VIDEO_RETRY_TEXT),
            ),
        ]
    }


def non_video_retryable_server_error_routes() -> dict[
    tuple[str, str],
    list[ScriptedResponse],
]:
    """Build scripted routes for non-video retryable server-error recovery."""
    return {
        ("POST", _NON_VIDEO_PATH): [
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
                body=openai_success_response(text=_NON_VIDEO_RETRY_TEXT),
            ),
        ]
    }


def non_video_non_retryable_routes() -> dict[tuple[str, str], list[ScriptedResponse]]:
    """Build scripted routes for a non-video non-retryable failure."""
    return {
        ("POST", _NON_VIDEO_PATH): [
            ScriptedResponse(
                status_code=400,
                headers={"Content-Type": "application/json"},
                body=openai_error_response(
                    status_code=400,
                    message=_NON_VIDEO_NON_RETRYABLE_MESSAGE,
                ),
            ),
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=openai_success_response(text="unexpected retry"),
            ),
        ]
    }


def non_video_auth_routes() -> dict[tuple[str, str], list[ScriptedResponse]]:
    """Build scripted routes for a non-video auth failure."""
    return {
        ("POST", _NON_VIDEO_PATH): [
            ScriptedResponse(
                status_code=401,
                headers={"Content-Type": "application/json"},
                body=openai_error_response(
                    status_code=401,
                    message=_NON_VIDEO_AUTH_MESSAGE,
                ),
            ),
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=openai_success_response(text="unexpected retry"),
            ),
        ]
    }


def video_retryable_routes() -> dict[tuple[str, str], list[ScriptedResponse]]:
    """Build scripted routes for native video retry recovery."""
    return {
        ("POST", _VIDEO_PATH): [
            ScriptedResponse(
                status_code=429,
                headers={"Content-Type": "text/plain; charset=utf-8"},
                body=b"retry me once",
            ),
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "text/event-stream"},
                body=aistudio_stream_response(text=json.dumps(_VIDEO_RETRY_JSON)),
            ),
        ]
    }


def video_retryable_server_error_routes() -> dict[
    tuple[str, str],
    list[ScriptedResponse],
]:
    """Build scripted routes for native video retryable server-error recovery."""
    return {
        ("POST", _VIDEO_PATH): [
            ScriptedResponse(
                status_code=503,
                headers={"Content-Type": "text/plain; charset=utf-8"},
                body=b"service unavailable once",
            ),
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "text/event-stream"},
                body=aistudio_stream_response(text=json.dumps(_VIDEO_RETRY_JSON)),
            ),
        ]
    }


def video_non_retryable_routes() -> dict[tuple[str, str], list[ScriptedResponse]]:
    """Build scripted routes for a native video non-retryable failure."""
    return {
        ("POST", _VIDEO_PATH): [
            ScriptedResponse(
                status_code=400,
                headers={"Content-Type": "text/plain; charset=utf-8"},
                body=_VIDEO_NON_RETRYABLE_MESSAGE.encode("utf-8"),
            ),
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "text/event-stream"},
                body=aistudio_stream_response(
                    text='{"status":"unexpected","server_attempts":2}'
                ),
            ),
        ]
    }


def video_auth_routes() -> dict[tuple[str, str], list[ScriptedResponse]]:
    """Build scripted routes for a native video auth failure."""
    return {
        ("POST", _VIDEO_PATH): [
            ScriptedResponse(
                status_code=401,
                headers={"Content-Type": "text/plain; charset=utf-8"},
                body=_VIDEO_AUTH_MESSAGE.encode("utf-8"),
            ),
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "text/event-stream"},
                body=aistudio_stream_response(
                    text='{"status":"unexpected","server_attempts":2}'
                ),
            ),
        ]
    }


# =============================================================================
# Pipeline
# =============================================================================


def run_non_video_retry_pipeline(*, server_base_url: str) -> RetryWorkerResult:
    """Run the retryable AI Studio non-video scenario."""
    # This worker path isolates a recoverable failure on the regular text/media path.
    return run_retry_worker(
        case=_NON_VIDEO_CASE,
        scenario="retryable",
        server_base_url=server_base_url,
    )


def run_non_video_non_retryable_pipeline(*, server_base_url: str) -> RetryWorkerResult:
    """Run the non-retryable AI Studio non-video scenario."""
    # This worker path isolates a permanent failure on the regular text/media path.
    return run_retry_worker(
        case=_NON_VIDEO_CASE,
        scenario="non_retryable",
        server_base_url=server_base_url,
    )


def run_video_retry_pipeline(*, server_base_url: str) -> RetryWorkerResult:
    """Run the retryable AI Studio native video scenario."""
    # This worker path isolates a recoverable failure on the native video endpoint.
    return run_retry_worker(
        case=_VIDEO_CASE,
        scenario="retryable",
        server_base_url=server_base_url,
    )


def run_video_non_retryable_pipeline(*, server_base_url: str) -> RetryWorkerResult:
    """Run the non-retryable AI Studio native video scenario."""
    # This worker path isolates a permanent failure on the native video endpoint.
    return run_retry_worker(
        case=_VIDEO_CASE,
        scenario="non_retryable",
        server_base_url=server_base_url,
    )


# =============================================================================
# Assertions
# =============================================================================


def assert_non_video_retry_response(
    response: RetryWorkerResult,
    *,
    server: ScriptedHTTPServer,
) -> None:
    """Assert the non-video retry recovery response."""
    # The OpenAI-compatible AI Studio path should recover successfully.
    assert response.returncode == 0
    assert response.ok is True, response.stderr or response.error_message
    # The final text proves the success came back after the retry.
    assert response.output_text == _NON_VIDEO_RETRY_TEXT
    # Two hits on the non-video endpoint prove one retry happened.
    assert server.request_count("POST", _NON_VIDEO_PATH) == 2


def assert_non_video_non_retryable_error(
    result: RetryWorkerResult,
    *,
    server: ScriptedHTTPServer,
    expected_message: str,
) -> None:
    """Assert the non-video non-retryable public error."""
    # The worker should surface a failure outcome, not crash.
    assert result.returncode == 0
    assert result.ok is False
    # Non-retryable non-video failures must stay provider errors.
    assert result.error_type == "ProviderError"
    assert expected_message in (result.error_message or "")
    # One hit proves fail-fast behavior on the non-video path.
    assert server.request_count("POST", _NON_VIDEO_PATH) == 1


def assert_video_retry_response(
    response: RetryWorkerResult,
    *,
    server: ScriptedHTTPServer,
) -> None:
    """Assert the native video retry recovery response."""
    # The native video path should also recover and return valid structured data.
    assert response.returncode == 0
    assert response.ok is True, response.stderr or response.error_message
    parsed = VideoRetryReport.model_validate_json(response.output_text)
    # Parsing the structured output proves the recovered response is not just
    # any text payload but the exact JSON shape expected on the video path.
    assert parsed == VideoRetryReport.model_validate(_VIDEO_RETRY_JSON)
    # Two video-endpoint hits prove the retry happened on the native path too.
    assert server.request_count("POST", _VIDEO_PATH) == 2


def assert_video_non_retryable_error(
    result: RetryWorkerResult,
    *,
    server: ScriptedHTTPServer,
    expected_message: str,
) -> None:
    """Assert the native video non-retryable public error."""
    # The worker should finish with a clear failure outcome.
    assert result.returncode == 0
    assert result.ok is False
    # Non-retryable video failures must stay visible as provider errors.
    assert result.error_type == "ProviderError"
    assert expected_message in (result.error_message or "")
    # One hit proves the native video path did not retry when it should not.
    assert server.request_count("POST", _VIDEO_PATH) == 1


# =============================================================================
# Tests
# =============================================================================


def test_non_video_retryable_failure_retries_then_succeeds() -> None:
    """Verify retryable AI Studio non-video failures are retried."""
    with ScriptedHTTPServer(port=_PORT, routes=non_video_retryable_routes()) as server:
        # First run the recoverable non-video path.
        response = run_non_video_retry_pipeline(server_base_url=server.base_url)
        assert_non_video_retry_response(response, server=server)


def test_non_video_retryable_server_error_retries_then_succeeds() -> None:
    """Verify retryable AI Studio non-video server errors are retried."""
    with ScriptedHTTPServer(
        port=_PORT,
        routes=non_video_retryable_server_error_routes(),
    ) as server:
        response = run_non_video_retry_pipeline(server_base_url=server.base_url)
        assert_non_video_retry_response(response, server=server)


def test_non_video_non_retryable_failure_does_not_retry() -> None:
    """Verify non-retryable AI Studio non-video failures do not retry."""
    with ScriptedHTTPServer(
        port=_PORT,
        routes=non_video_non_retryable_routes(),
    ) as server:
        # Run the permanent non-video failure path once.
        result = run_non_video_non_retryable_pipeline(server_base_url=server.base_url)
        assert_non_video_non_retryable_error(
            result,
            server=server,
            expected_message=_NON_VIDEO_NON_RETRYABLE_MESSAGE,
        )


def test_non_video_auth_failure_does_not_retry() -> None:
    """Verify non-retryable AI Studio non-video auth failures do not retry."""
    with ScriptedHTTPServer(port=_PORT, routes=non_video_auth_routes()) as server:
        result = run_non_video_non_retryable_pipeline(server_base_url=server.base_url)
        assert_non_video_non_retryable_error(
            result,
            server=server,
            expected_message=_NON_VIDEO_AUTH_MESSAGE,
        )


def test_video_retryable_failure_retries_then_succeeds() -> None:
    """Verify retryable AI Studio video failures are retried."""
    with ScriptedHTTPServer(port=_PORT, routes=video_retryable_routes()) as server:
        # Then repeat the recovery proof on the native video path.
        response = run_video_retry_pipeline(server_base_url=server.base_url)
        assert_video_retry_response(response, server=server)


def test_video_retryable_server_error_retries_then_succeeds() -> None:
    """Verify retryable AI Studio video server errors are retried."""
    with ScriptedHTTPServer(
        port=_PORT,
        routes=video_retryable_server_error_routes(),
    ) as server:
        response = run_video_retry_pipeline(server_base_url=server.base_url)
        assert_video_retry_response(response, server=server)


def test_video_non_retryable_failure_does_not_retry() -> None:
    """Verify non-retryable AI Studio video failures do not retry."""
    with ScriptedHTTPServer(port=_PORT, routes=video_non_retryable_routes()) as server:
        # And prove the native video path also fails fast on permanent errors.
        result = run_video_non_retryable_pipeline(server_base_url=server.base_url)
        assert_video_non_retryable_error(
            result,
            server=server,
            expected_message=_VIDEO_NON_RETRYABLE_MESSAGE,
        )


def test_video_auth_failure_does_not_retry() -> None:
    """Verify non-retryable AI Studio video auth failures do not retry."""
    with ScriptedHTTPServer(port=_PORT, routes=video_auth_routes()) as server:
        result = run_video_non_retryable_pipeline(server_base_url=server.base_url)
        assert_video_non_retryable_error(
            result,
            server=server,
            expected_message=_VIDEO_AUTH_MESSAGE,
        )


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the retry demo flow for manual execution."""
    console.demo_intro(__doc__)
    with ScriptedHTTPServer(port=_PORT, routes=non_video_retryable_routes()) as server:
        # Show the recoverable non-video branch first.
        non_video_response = run_non_video_retry_pipeline(
            server_base_url=server.base_url
        )
        assert_non_video_retry_response(non_video_response, server=server)

        console.demo_step(
            "What Happened On The Non-Video Success Path",
            "The regular text/media route retried once and then recovered.",
            details=[
                f"Final output: {non_video_response.output_text}",
                f"Non-video hits: {server.request_count('POST', _NON_VIDEO_PATH)}",
            ],
        )

    with ScriptedHTTPServer(
        port=_PORT,
        routes=non_video_non_retryable_routes(),
    ) as server:
        # Then contrast it with the permanent non-video failure.
        non_video_error = run_non_video_non_retryable_pipeline(
            server_base_url=server.base_url
        )
        assert_non_video_non_retryable_error(
            non_video_error,
            server=server,
            expected_message=_NON_VIDEO_NON_RETRYABLE_MESSAGE,
        )

        console.demo_step(
            "What Happened On The Non-Video Fail-Fast Path",
            "A non-retryable non-video error stopped immediately instead of looping.",
            details=[
                "Public error: "
                f"{non_video_error.error_type}: {non_video_error.error_message}",
                f"Non-video hits: {server.request_count('POST', _NON_VIDEO_PATH)}",
            ],
        )

    with ScriptedHTTPServer(port=_PORT, routes=video_retryable_routes()) as server:
        # Repeat the same recovery story on the native video path.
        video_response = run_video_retry_pipeline(server_base_url=server.base_url)
        assert_video_retry_response(video_response, server=server)

        console.demo_step(
            "What Happened On The Video Success Path",
            "The native video route also retried once and then succeeded.",
            details=[
                f"Final output: {video_response.output_text}",
                f"Video hits: {server.request_count('POST', _VIDEO_PATH)}",
            ],
        )

    with ScriptedHTTPServer(port=_PORT, routes=video_non_retryable_routes()) as server:
        # Finally, show that permanent native video errors still fail fast.
        video_error = run_video_non_retryable_pipeline(server_base_url=server.base_url)
        assert_video_non_retryable_error(
            video_error,
            server=server,
            expected_message=_VIDEO_NON_RETRYABLE_MESSAGE,
        )

        console.demo_step(
            "What Happened On The Video Fail-Fast Path",
            "A non-retryable video error was surfaced immediately as a public failure.",
            details=[
                f"Public error: {video_error.error_type}: {video_error.error_message}",
                f"Video hits: {server.request_count('POST', _VIDEO_PATH)}",
            ],
        )
    console.demo_outcome(
        "This passed because both AI Studio execution paths behaved "
        "consistently: retryable failures recovered once, and "
        "non-retryable failures stopped clearly."
    )


if __name__ == "__main__":
    main()
# %%
