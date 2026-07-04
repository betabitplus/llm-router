# %%
"""LLM Router e2e: concurrency isolation.

Why:
    Verifies that concurrent public requests do not leak session or routing
    state across separate routers, even when they share one async client
    singleton in-process.

Covers:
    Area: concurrency and isolation
    Behavior: concurrent `aquery(...)` with separate sessions
    Interface: `LLMRouter(...).aquery(...)`

Checks:
    If the concurrent worker scenario runs successfully, then the worker exits cleanly
    with `ok=True`.
    If the alpha request stays isolated, then its visible answer is `ALPHA`.
    If the beta request stays isolated, then its visible answer is `BETA`.
    If alpha session history is isolated, then it contains exactly 2 messages.
    If beta session history is isolated, then it contains exactly 2 messages.
    If alpha prompt state is isolated, then its recorded user parts are exactly `Reply
    only ALPHA.`.
    If beta prompt state is isolated, then its recorded user parts are exactly `Reply
    only BETA.`.
    If concurrent execution avoids duplicate provider work, then the server sees exactly
    2 requests.
    If alpha routing state is isolated, then its routing trace is one successful route-0
    entry.
    If beta routing state is isolated, then its routing trace is one successful route-0
    entry.

Notes:
    This scenario is hermetic by construction because it uses a local
    body-aware HTTP server started inside the worker process.

Examples:
    Run manually:
        uv run python -m \
            tests.llm_router.e2e.session_state_and_isolation.test_concurrency_isolation_pipeline

    Run as test:
        pytest \
            tests/llm_router/e2e/session_state_and_isolation/test_concurrency_isolation_pipeline.py
"""

from __future__ import annotations

import pytest

from tests.llm_router.support.workers.concurrency_isolation import (
    ConcurrencyIsolationWorkerResult,
    run_concurrency_isolation_inprocess,
)
from tests.support.console import console

pytestmark = [
    pytest.mark.e2e_behavior,
    pytest.mark.cap_resilience,
    pytest.mark.cap_session,
    pytest.mark.hermetic,
]


# =============================================================================
# Scenario
# =============================================================================

# No module-level scenario constants are needed here.


# =============================================================================
# Helpers
# =============================================================================

# No local helpers for this scenario.


# =============================================================================
# Pipeline
# =============================================================================


def run_pipeline() -> ConcurrencyIsolationWorkerResult:
    """Run the concurrency-isolation scenario."""
    # The worker sets up the concurrent flow end to end, so this wrapper keeps
    # the public story simple for the reader.
    return run_concurrency_isolation_inprocess()


# =============================================================================
# Assertions
# =============================================================================


def assert_pipeline_result(result: ConcurrencyIsolationWorkerResult) -> None:
    """Assert concurrent requests stay isolated."""
    # Start by proving the worker completed successfully.
    assert result.returncode == 0
    assert result.ok is True, result.stderr or result.error_message

    # Each concurrent request should get its own answer, not a mixed result.
    assert result.alpha_text == "ALPHA"
    assert result.beta_text == "BETA"

    # Each session should contain only one user turn and one assistant turn.
    assert result.alpha_history_length == 2
    assert result.beta_history_length == 2

    # The recorded user parts are the most direct proof that prompts did not
    # leak across sessions.
    assert result.alpha_user_parts == ["Reply only ALPHA."]
    assert result.beta_user_parts == ["Reply only BETA."]

    # Exactly two server hits means each request made one independent provider
    # call rather than duplicating or replaying work.
    assert result.request_count == 2

    # Finally, the routing traces must stay separate and successful as well.
    assert len(result.alpha_routing_trace) == 1
    assert len(result.beta_routing_trace) == 1
    assert result.alpha_routing_trace[0]["route_index"] == 0
    assert result.beta_routing_trace[0]["route_index"] == 0
    assert result.alpha_routing_trace[0]["error_type"] is None
    assert result.beta_routing_trace[0]["error_type"] is None


# =============================================================================
# Tests
# =============================================================================


def test_concurrent_requests_keep_sessions_and_traces_isolated() -> None:
    """Verify concurrent requests do not leak session or routing state."""
    # First run the full concurrent scenario once.
    result = run_pipeline()
    # Then prove that answers, histories, and traces stayed separate.
    assert_pipeline_result(result)


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the concurrency-isolation demo flow for manual execution."""
    # Run the same concurrent flow the test validates.
    result = run_pipeline()
    assert_pipeline_result(result)

    console.demo_intro(__doc__)
    console.demo_step(
        "What Happened",
        "Two requests ran at the same time, and each one kept its own "
        "answer, history, and trace.",
        details=[
            f"Alpha answer: {result.alpha_text}",
            f"Beta answer: {result.beta_text}",
            f"Alpha history length: {result.alpha_history_length}",
            f"Beta history length: {result.beta_history_length}",
            f"Alpha user parts: {result.alpha_user_parts}",
            f"Beta user parts: {result.beta_user_parts}",
            f"Alpha routing: {result.alpha_routing_trace}",
            f"Beta routing: {result.beta_routing_trace}",
            f"Request count: {result.request_count}",
        ],
    )
    console.demo_outcome(
        "This passed because the two in-flight requests did not leak "
        "content, session state, or routing metadata into each other."
    )


if __name__ == "__main__":
    main()
# %%
