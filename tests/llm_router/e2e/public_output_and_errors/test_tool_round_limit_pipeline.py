# %%
"""LLM Router e2e: tool-round limit behavior.

Why:
    Verifies the public contract when the model keeps requesting tools until
    `max_tool_rounds` is exhausted.

Covers:
    Area: tool orchestration
    Behavior: tool-round exhaustion
    Interface: `LLMRouter(...).query(..., tools=[...], max_tool_rounds=...)`

Checks:
    If the tool loop reaches the configured round limit, then the worker still ends
    successfully.
    If the round limit stops final answer generation, then `output_text` is empty.
    If the loop reaches exactly two rounds, then the provider endpoint is hit exactly
    twice.
    If the runtime trace preserves both tool rounds, then `tool_trace` has length `2`.
    If the last outstanding tool request is exposed publicly, then `tool_calls` has
    length `1` and its name is `ping`.
    If the outstanding tool request is preserved exactly, then its args are `{"value":
    7}`.
    If both recorded tool rounds match the scripted tool, then every traced tool name is
    `ping`.

Notes:
    This scenario is hermetic by construction because it talks only to a local
    scripted HTTP server.

Examples:
    Run manually:
        uv run python -m \
            tests.llm_router.e2e.public_output_and_errors.test_tool_round_limit_pipeline

    Run as test:
        pytest \
            tests/llm_router/e2e/public_output_and_errors/test_tool_round_limit_pipeline.py
"""

from __future__ import annotations

import pytest

from llm_router import Model
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    google_generate_path,
    openai_chat_path,
)
from tests.llm_router.support.workers.tool_failure import (
    google_tool_call_response,
    openai_tool_call_response,
)
from tests.llm_router.support.workers.tool_round_limit import (
    ToolRoundLimitWorkerResult,
    run_tool_round_limit_worker,
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


def openai_tool_round_routes() -> dict[tuple[str, str], list[ScriptedResponse]]:
    """Build scripted OpenAI-compatible repeated-tool routes."""
    return {
        ("POST", _OPENAI_PATH): [
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=openai_tool_call_response(tool_name="ping", args={"value": 7}),
            ),
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=openai_tool_call_response(tool_name="ping", args={"value": 7}),
            ),
        ]
    }


def google_tool_round_routes() -> dict[tuple[str, str], list[ScriptedResponse]]:
    """Build scripted Google repeated-tool routes."""
    return {
        ("POST", _GOOGLE_PATH): [
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=google_tool_call_response(tool_name="ping", args={"value": 7}),
            ),
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=google_tool_call_response(tool_name="ping", args={"value": 7}),
            ),
        ]
    }


# =============================================================================
# Pipeline
# =============================================================================


def run_openai_tool_round_limit_pipeline(
    *,
    server_base_url: str,
) -> ToolRoundLimitWorkerResult:
    """Run the OpenAI-compatible representative tool-round-limit scenario."""
    # This worker path isolates a model that keeps asking for tools past the limit.
    return run_tool_round_limit_worker(case="openai", server_base_url=server_base_url)


def run_google_tool_round_limit_pipeline(
    *,
    server_base_url: str,
) -> ToolRoundLimitWorkerResult:
    """Run the Google representative tool-round-limit scenario."""
    # This worker path repeats the same endless-tool pattern on the Google side.
    return run_tool_round_limit_worker(case="google", server_base_url=server_base_url)


# =============================================================================
# Assertions
# =============================================================================


def assert_tool_round_limit_result(
    result: ToolRoundLimitWorkerResult,
    *,
    server: ScriptedHTTPServer,
    path: str,
) -> None:
    """Assert the public tool-round-limit contract."""
    # The worker should end successfully because hitting the round limit is a
    # supported outcome, not an error.
    assert result.returncode == 0
    assert result.ok is True, result.stderr or result.error_message
    # No final assistant text should be fabricated once the limit is exhausted.
    assert result.output_text == ""
    # Two provider hits prove the tool loop reached exactly two rounds.
    assert server.request_count("POST", path) == 2
    # The trace should record both tool steps, while the final tool_calls field
    # exposes the last outstanding tool request.
    assert len(result.tool_trace) == 2
    assert len(result.tool_calls) == 1
    assert {step["tool_name"] for step in result.tool_trace} == {"ping"}
    assert result.tool_calls[0]["name"] == "ping"
    assert result.tool_calls[0]["args"] == {"value": 7}


# =============================================================================
# Tests
# =============================================================================


def test_openai_tool_round_limit_returns_last_tool_call() -> None:
    """Verify the OpenAI tool loop stops at the configured round limit."""
    with ScriptedHTTPServer(port=_PORT, routes=openai_tool_round_routes()) as server:
        # First run the repeated-tool scenario once.
        result = run_openai_tool_round_limit_pipeline(server_base_url=server.base_url)
        # Then prove the router stopped at the limit and exposed the last tool state.
        assert_tool_round_limit_result(result, server=server, path=_OPENAI_PATH)


def test_google_tool_round_limit_returns_last_tool_call() -> None:
    """Verify the GenAI tool loop stops at the configured round limit."""
    with ScriptedHTTPServer(port=_PORT, routes=google_tool_round_routes()) as server:
        # Repeat the same proof on the Google implementation.
        result = run_google_tool_round_limit_pipeline(server_base_url=server.base_url)
        assert_tool_round_limit_result(result, server=server, path=_GOOGLE_PATH)


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the tool-round-limit demo flow for manual execution."""
    console.demo_intro(__doc__)
    with ScriptedHTTPServer(port=_PORT, routes=openai_tool_round_routes()) as server:
        # Show one representative tool loop first.
        openai_result = run_openai_tool_round_limit_pipeline(
            server_base_url=server.base_url
        )
        assert_tool_round_limit_result(openai_result, server=server, path=_OPENAI_PATH)

        console.demo_step(
            "What Happened On The OpenAI-Compatible Tool Loop",
            "The model kept asking for tools until the configured "
            "round limit stopped the flow.",
            details=[
                f"Final output text: {openai_result.output_text!r}",
                f"Tool trace: {openai_result.tool_trace}",
                f"Last tool calls: {openai_result.tool_calls}",
                f"Server hits: {server.request_count('POST', _OPENAI_PATH)}",
            ],
        )

    with ScriptedHTTPServer(port=_PORT, routes=google_tool_round_routes()) as server:
        # Then show the same limit behavior on the second implementation.
        google_result = run_google_tool_round_limit_pipeline(
            server_base_url=server.base_url
        )
        assert_tool_round_limit_result(google_result, server=server, path=_GOOGLE_PATH)

        console.demo_step(
            "What Happened On The Google Tool Loop",
            "The Google implementation stopped at the same round limit "
            "and exposed the last tool state.",
            details=[
                f"Final output text: {google_result.output_text!r}",
                f"Tool trace: {google_result.tool_trace}",
                f"Last tool calls: {google_result.tool_calls}",
                f"Server hits: {server.request_count('POST', _GOOGLE_PATH)}",
            ],
        )
    console.demo_outcome(
        "This passed because both tool implementations respected the "
        "configured limit and returned the remaining tool state in a "
        "consistent way."
    )


if __name__ == "__main__":
    main()
# %%
