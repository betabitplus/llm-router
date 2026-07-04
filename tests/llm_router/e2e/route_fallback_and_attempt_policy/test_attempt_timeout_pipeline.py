# %%
"""LLM Router e2e: attempt-timeout routing.

Why:
    Verifies that the public router enforces per-attempt timeout policy and
    routes accordingly.

Covers:
    Area: routing layer
    Behavior: attempt timeout fallback, terminal attempt timeout
    Interface: `LLMRouter([RouterProfile(...), ...])`, `query(...)`

Checks:
    If the fallback-after-timeout branch is exercised, then the worker completes
    successfully.
    If the first attempt times out but a fallback route exists, then the final output is
    the scripted fallback text.
    If timeout fallback really happens, then the scripted server sees exactly 2 hits.
    If timeout fallback really happens, then the routing trace has 2 entries with
    `TimeoutError` first and a successful route index `1` second.
    If the terminal-timeout branch is exercised, then the worker still exits cleanly
    with `ok=False`.
    If no fallback route exists, then the public error type is `TimeoutError`.
    If terminal timeout really fails fast, then the scripted server sees exactly 1 hit.

Notes:
    This scenario is hermetic by construction because it talks only to a local
    scripted HTTP server.

Examples:
    Run manually:
        uv run python -m \
            tests.llm_router.e2e.route_fallback_and_attempt_policy.test_attempt_timeout_pipeline

    Run as test:
        pytest \
            tests/llm_router/e2e/route_fallback_and_attempt_policy/test_attempt_timeout_pipeline.py
"""

from __future__ import annotations

import pytest

from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)
from tests.llm_router.support.workers.timeout import (
    TimeoutWorkerResult,
    run_timeout_inprocess,
)
from tests.support.console import console

pytestmark = [
    pytest.mark.e2e_behavior,
    pytest.mark.cap_routing,
    pytest.mark.cap_resilience,
    pytest.mark.hermetic,
]


# =============================================================================
# Scenario
# =============================================================================

# One local provider-shaped endpoint is enough for this scenario because we are
# proving router behavior, not provider diversity.
_PORT = 0
_PATH = openai_chat_path()

# This is the exact success text we expect only after the fallback attempt wins.
_TIMEOUT_TEXT = "timeout fallback ok on server-attempt-2"

# NOTE: This delay must be comfortably above the workers' per-attempt timeout
# so the first attempt deterministically times out even under CI load.
_TIMEOUT_DELAY_SECONDS = 2.0


# =============================================================================
# Helpers
# =============================================================================


def fallback_after_timeout_routes() -> dict[tuple[str, str], list[ScriptedResponse]]:
    """Build scripted routes for timeout fallback recovery."""
    return {
        ("POST", _PATH): [
            # Attempt 1 looks like a normal success payload, but it sleeps long
            # enough to become a timeout from the router's point of view.
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=openai_success_response(text="timed-out first attempt"),
                delay_seconds=_TIMEOUT_DELAY_SECONDS,
            ),
            # Attempt 2 returns immediately and should become the visible result.
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=openai_success_response(text=_TIMEOUT_TEXT),
            ),
        ]
    }


def terminal_timeout_routes() -> dict[tuple[str, str], list[ScriptedResponse]]:
    """Build scripted routes for a terminal attempt timeout."""
    return {
        ("POST", _PATH): [
            # Here we deliberately provide only the slow response so the router
            # has no healthy fallback path to recover to.
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=openai_success_response(text="timed-out only attempt"),
                delay_seconds=_TIMEOUT_DELAY_SECONDS,
            ),
        ]
    }


# =============================================================================
# Pipeline
# =============================================================================


def run_fallback_after_timeout_pipeline(*, server_base_url: str) -> TimeoutWorkerResult:
    """Run the timeout-fallback scenario."""
    # Keep the execution path tiny: one worker call, one scenario name, one
    # scripted server URL. That makes it easy to see what the router is doing.
    return run_timeout_inprocess(
        scenario="fallback_after_timeout",
        server_base_url=server_base_url,
    )


def run_terminal_timeout_pipeline(*, server_base_url: str) -> TimeoutWorkerResult:
    """Run the terminal-timeout scenario."""
    # This uses the same worker machinery as the recovery case, so the only
    # meaningful difference is the scripted timeout-only route setup.
    return run_timeout_inprocess(
        scenario="terminal_timeout",
        server_base_url=server_base_url,
    )


# =============================================================================
# Assertions
# =============================================================================


def assert_fallback_after_timeout_response(
    result: TimeoutWorkerResult,
    *,
    server: ScriptedHTTPServer,
) -> None:
    """Assert attempt timeout falls back to the next route."""
    # The worker itself must complete cleanly so the rest of the assertions are
    # about router behavior, not worker-process setup.
    assert result.returncode == 0
    assert result.ok is True, result.stderr or result.error_message

    # The final answer should come from the successful fallback route.
    assert result.output_text == _TIMEOUT_TEXT

    # Two hits prove we really made an initial attempt and then a retry/fallback
    # attempt against the local scripted server.
    assert server.request_count("POST", _PATH) == 2

    # The routing trace should tell the same story: first attempt timed out,
    # second attempt succeeded on route index 1.
    assert len(result.routing_trace) == 2
    assert result.routing_trace[0]["error_type"] == "TimeoutError"
    assert result.routing_trace[1]["error_type"] is None
    assert result.routing_trace[1]["route_index"] == 1


def assert_terminal_timeout_error(
    result: TimeoutWorkerResult,
    *,
    server: ScriptedHTTPServer,
) -> None:
    """Assert a terminal attempt timeout surfaces publicly."""
    # The worker still needs to finish normally even though the router should
    # report a timeout outcome.
    assert result.returncode == 0
    assert result.ok is False

    # With no fallback route available, the public error should stay a timeout.
    assert result.error_type == "TimeoutError"

    # One hit proves the router did not invent an extra hidden retry.
    assert server.request_count("POST", _PATH) == 1


# =============================================================================
# Tests
# =============================================================================


def test_timed_out_attempt_falls_back_and_succeeds() -> None:
    """Verify attempt timeout triggers fallback to the next route."""
    with ScriptedHTTPServer(
        port=_PORT,
        routes=fallback_after_timeout_routes(),
    ) as server:
        # First run the exact public flow we want to reason about.
        result = run_fallback_after_timeout_pipeline(server_base_url=server.base_url)

        # Then explain success through the dedicated assertion helper.
        assert_fallback_after_timeout_response(result, server=server)


def test_terminal_attempt_timeout_raises() -> None:
    """Verify a terminal attempt timeout raises when no fallback exists."""
    with ScriptedHTTPServer(port=_PORT, routes=terminal_timeout_routes()) as server:
        # Run the same router machinery, but without any recoverable second route.
        result = run_terminal_timeout_pipeline(server_base_url=server.base_url)

        # The helper now proves that the timeout surfaced publicly.
        assert_terminal_timeout_error(result, server=server)


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the attempt-timeout demo flow for manual execution."""
    console.demo_intro(__doc__)
    with ScriptedHTTPServer(
        port=_PORT,
        routes=fallback_after_timeout_routes(),
    ) as server:
        # Show the recovery branch first so the reader sees the optimistic path.
        fallback_result = run_fallback_after_timeout_pipeline(
            server_base_url=server.base_url
        )
        assert_fallback_after_timeout_response(fallback_result, server=server)

        console.demo_step(
            "What Happened On The Recovery Path",
            "The first attempt timed out, and the router recovered by "
            "moving to the fallback route.",
            details=[
                f"Final output: {fallback_result.output_text}",
                f"Routing trace: {fallback_result.routing_trace}",
                f"Server hits: {server.request_count('POST', _PATH)}",
            ],
        )

    with ScriptedHTTPServer(port=_PORT, routes=terminal_timeout_routes()) as server:
        # Then show the same logic when recovery is impossible.
        terminal_result = run_terminal_timeout_pipeline(server_base_url=server.base_url)
        assert_terminal_timeout_error(terminal_result, server=server)

        console.demo_step(
            "What Happened Without A Fallback",
            "When no backup route existed, the timeout surfaced "
            "publicly instead of silently succeeding.",
            details=[
                "Public error: "
                f"{terminal_result.error_type}: {terminal_result.error_message}",
                f"Server hits: {server.request_count('POST', _PATH)}",
            ],
        )
    console.demo_outcome(
        "This passed because the router behaved safely in both "
        "directions: it recovered when a fallback was available and "
        "failed clearly when it was not."
    )


if __name__ == "__main__":
    main()
# %%
