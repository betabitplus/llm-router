# %%
"""LLM Router e2e: tool failure behavior.

Why:
    Verifies that local tool execution failures surface through one consistent
    public error contract across the supported tool-calling implementations.

Covers:
    Area: tool orchestration
    Behavior: failing local tool execution
    Interface: `LLMRouter(...).query(..., tools=[...])`

Checks:
    If a tool fails locally, then the worker ends in a clean failure result.
    If the public boundary preserves the cause, then the error type is
    `ToolExecutionError`.
    If failing-call context is preserved, then the public message mentions `explode`.
    If failing-call context is preserved, then the public message also mentions
    `value=7`.
    If the tool loop stops immediately after the failure, then the provider endpoint is
    hit exactly once.

Notes:
    This scenario is hermetic by construction because it talks only to a local
    scripted HTTP server.

Examples:
    Run manually:
        uv run python -m \
            tests.llm_router.e2e.public_output_and_errors.test_tool_failure_pipeline

    Run as test:
        pytest \
            tests/llm_router/e2e/public_output_and_errors/test_tool_failure_pipeline.py
"""

from __future__ import annotations

import pytest

from llm_router import Model, ToolExecutionError
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    google_generate_path,
    openai_chat_path,
)
from tests.llm_router.support.workers.tool_failure import (
    ToolFailureWorkerResult,
    google_tool_call_response,
    openai_tool_call_response,
    run_tool_failure_worker,
)
from tests.support.console import console

pytestmark = [
    pytest.mark.e2e_behavior,
    pytest.mark.cap_tools,
    pytest.mark.cap_resilience,
    pytest.mark.hermetic,
]


# =============================================================================
# Scenario
# =============================================================================

_PORT = 0
_OPENAI_PATH = openai_chat_path()
_GOOGLE_PATH = google_generate_path(model=Model.GEMINI_3_FLASH)


# =============================================================================
# Helpers
# =============================================================================


def openai_tool_failure_routes() -> dict[tuple[str, str], list[ScriptedResponse]]:
    """Build the OpenAI-compatible scripted tool-call route."""
    return {
        ("POST", _OPENAI_PATH): [
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=openai_tool_call_response(tool_name="explode", args={"value": 7}),
            )
        ]
    }


def google_tool_failure_routes() -> dict[tuple[str, str], list[ScriptedResponse]]:
    """Build the Google GenAI scripted tool-call route."""
    return {
        ("POST", _GOOGLE_PATH): [
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=google_tool_call_response(tool_name="explode", args={"value": 7}),
            )
        ]
    }


# =============================================================================
# Pipeline
# =============================================================================


def run_openai_tool_failure_pipeline(
    *,
    server_base_url: str,
) -> ToolFailureWorkerResult:
    """Run the OpenAI-compatible representative tool-failure scenario."""
    # This worker path isolates one tool call that fails locally.
    return run_tool_failure_worker(case="openai", server_base_url=server_base_url)


def run_google_tool_failure_pipeline(
    *,
    server_base_url: str,
) -> ToolFailureWorkerResult:
    """Run the Google representative tool-failure scenario."""
    # This worker path repeats the same local tool failure on the Google side.
    return run_tool_failure_worker(case="google", server_base_url=server_base_url)


# =============================================================================
# Assertions
# =============================================================================


def assert_tool_failure_result(
    result: ToolFailureWorkerResult,
    *,
    server: ScriptedHTTPServer,
    path: str,
) -> None:
    """Assert the public tool-failure contract."""
    # The worker should finish with a clean failure result.
    assert result.returncode == 0
    assert result.ok is False
    # The public error type must specifically identify local tool execution.
    assert result.error_type == ToolExecutionError.__name__
    # The error message should preserve enough context to identify the failing
    # tool invocation.
    assert "explode" in (result.error_message or "")
    assert "value=7" in (result.error_message or "")
    # One provider hit proves the flow stopped at the tool failure and did not
    # continue into more model turns.
    assert server.request_count("POST", path) == 1


# =============================================================================
# Tests
# =============================================================================


def test_openai_tool_failure_raises_public_error() -> None:
    """Verify a failing tool raises ToolExecutionError on the OpenAI tool loop."""
    with ScriptedHTTPServer(port=_PORT, routes=openai_tool_failure_routes()) as server:
        # First run the failing-tool path once.
        result = run_openai_tool_failure_pipeline(server_base_url=server.base_url)
        # Then prove the public failure came from local tool execution.
        assert_tool_failure_result(result, server=server, path=_OPENAI_PATH)


def test_google_tool_failure_raises_public_error() -> None:
    """Verify a failing tool raises ToolExecutionError on the GenAI tool loop."""
    with ScriptedHTTPServer(port=_PORT, routes=google_tool_failure_routes()) as server:
        # Repeat the same proof on the Google implementation.
        result = run_google_tool_failure_pipeline(server_base_url=server.base_url)
        assert_tool_failure_result(result, server=server, path=_GOOGLE_PATH)


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the tool-failure demo flow for manual execution."""
    console.demo_intro(__doc__)
    with ScriptedHTTPServer(port=_PORT, routes=openai_tool_failure_routes()) as server:
        # Show the OpenAI-compatible failure shape first.
        openai_result = run_openai_tool_failure_pipeline(
            server_base_url=server.base_url
        )
        assert_tool_failure_result(openai_result, server=server, path=_OPENAI_PATH)

        console.demo_step(
            "What Happened On The OpenAI-Compatible Tool Loop",
            "The tool raised a local failure, and the flow stopped "
            "immediately with a public tool error.",
            details=[
                "Public error: "
                f"{openai_result.error_type}: {openai_result.error_message}",
                f"Server hits: {server.request_count('POST', _OPENAI_PATH)}",
            ],
        )

    with ScriptedHTTPServer(port=_PORT, routes=google_tool_failure_routes()) as server:
        # Then show the same public contract on the Google implementation.
        google_result = run_google_tool_failure_pipeline(
            server_base_url=server.base_url
        )
        assert_tool_failure_result(google_result, server=server, path=_GOOGLE_PATH)

        console.demo_step(
            "What Happened On The Google Tool Loop",
            "The same failing tool produced the same public error contract "
            "on the Google implementation.",
            details=[
                "Public error: "
                f"{google_result.error_type}: {google_result.error_message}",
                f"Server hits: {server.request_count('POST', _GOOGLE_PATH)}",
            ],
        )
    console.demo_outcome(
        "This passed because both tool-calling implementations reported "
        "the same kind of public failure instead of diverging."
    )


if __name__ == "__main__":
    main()
# %%
