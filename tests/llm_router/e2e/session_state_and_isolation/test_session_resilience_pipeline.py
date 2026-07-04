# %%
"""LLM Router e2e: session persistence after resilience behavior.

Why:
    Verifies that saved sessions preserve assistant metadata correctly even when
    the assistant reply succeeds only after timeout-driven fallback.

Covers:
    Area: session flow
    Behavior: timeout fallback, `Session.save(...)`, `Session.load(...)`, resume
    Interface: `LLMRouter(..., session=...)`, `query(...)`

Checks:
    If the timeout-fallback workflow succeeds, then the worker completes successfully.
    If the resumed session is asked to recall the code, then the final output is
    `81723`.
    If both turns survive persistence, then the saved history length is `4`.
    If each assistant turn times out once before fallback success, then the server sees
    2 OpenRouter hits and 2 Groq hits.
    If first-turn assistant metadata is preserved, then its provider and model stay
    `groq` and `llama-scout`, and usage keeps non-negative total tokens.
    If second-turn assistant metadata is preserved, then its provider and model stay
    `groq` and `llama-scout`, and usage keeps non-negative total tokens.
    If first-turn routing metadata is preserved, then its trace records OpenRouter route
    `0` failing with `TimeoutError` before Groq route `1` succeeds.
    If resumed-turn routing metadata is preserved, then its trace records the same
    OpenRouter-timeout and Groq-success pattern.
    If recorded request payloads stay consistent, then both OpenRouter and Groq payloads
    keep string `model` fields.

Notes:
    This scenario is hermetic by construction because it talks only to a local
    scripted HTTP server.

Examples:
    Run manually:
        uv run python -m \
            tests.llm_router.e2e.session_state_and_isolation.test_session_resilience_pipeline

    Run as test:
        pytest \
            tests/llm_router/e2e/session_state_and_isolation/test_session_resilience_pipeline.py
"""

from __future__ import annotations

import json

import pytest

from llm_router import Model, Provider
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_success_response,
)
from tests.llm_router.support.workers.session_resilience import (
    SessionResilienceWorkerResult,
    run_session_resilience_inprocess,
)
from tests.support.console import console

pytestmark = [
    pytest.mark.e2e_behavior,
    pytest.mark.cap_session,
    pytest.mark.cap_resilience,
    pytest.mark.hermetic,
]


# =============================================================================
# Scenario
# =============================================================================

_PORT = 0
_PATH = openai_chat_path()
_OPENROUTER_PATH = f"/openrouter{_PATH}"
_GROQ_PATH = f"/groq{_PATH}"
# NOTE: This delay must be comfortably above the workers' per-attempt timeout
# so the timeout-fallback pattern is deterministic even under CI load.
_TIMEOUT_DELAY_SECONDS = 2.5


# =============================================================================
# Helpers
# =============================================================================


def session_resilience_routes() -> dict[tuple[str, str], list[ScriptedResponse]]:
    """Build scripted routes for session resume after timeout fallback."""
    return {
        ("POST", _OPENROUTER_PATH): [
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=openai_success_response(text="81723"),
                delay_seconds=_TIMEOUT_DELAY_SECONDS,
            ),
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=openai_success_response(text="81723"),
                delay_seconds=_TIMEOUT_DELAY_SECONDS,
            ),
        ],
        ("POST", _GROQ_PATH): [
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=openai_success_response(text="81723"),
            ),
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=openai_success_response(text="81723"),
            ),
        ],
    }


# =============================================================================
# Pipeline
# =============================================================================


def run_pipeline(*, server_base_url: str) -> SessionResilienceWorkerResult:
    """Run the session-resilience scenario."""
    # The worker owns the full save-resume flow so this wrapper keeps the test
    # story focused on the resilience outcome.
    return run_session_resilience_inprocess(
        scenario="resume_after_timeout_fallback",
        server_base_url=server_base_url,
    )


# =============================================================================
# Assertions
# =============================================================================


def assert_pipeline_result(
    result: SessionResilienceWorkerResult,
    *,
    server: ScriptedHTTPServer,
) -> None:
    """Assert the saved session preserves resilience metadata."""
    # The worker should end in success because the router is expected to recover.
    assert result.returncode == 0
    assert result.ok is True, result.stderr or result.error_message
    # The resumed conversation must still recall the remembered value.
    assert result.output_text.strip() == "81723"
    # Four saved history entries prove both turns survived persistence.
    assert result.saved_history_length == 4
    # Four server hits prove each assistant turn experienced one timeout and one
    # fallback success.
    assert server.request_count("POST", _OPENROUTER_PATH) == 2
    assert server.request_count("POST", _GROQ_PATH) == 2

    assert result.first_assistant_meta["provider"] == Provider.GROQ.value
    assert result.first_assistant_meta["model"] == Model.LLAMA_SCOUT.value
    assert result.first_assistant_meta["usage"]["total_tokens"] >= 0
    assert result.second_assistant_meta["provider"] == Provider.GROQ.value
    assert result.second_assistant_meta["model"] == Model.LLAMA_SCOUT.value
    assert result.second_assistant_meta["usage"]["total_tokens"] >= 0

    first_trace = result.first_assistant_meta["routing_trace"]
    # The first saved assistant metadata must preserve the timeout-then-success story.
    assert len(first_trace) == 2
    assert first_trace[0]["provider"] == Provider.OPENROUTER.value
    assert first_trace[0]["route_index"] == 0
    assert first_trace[0]["error_type"] == "TimeoutError"
    assert first_trace[1]["provider"] == Provider.GROQ.value
    assert first_trace[1]["route_index"] == 1
    assert first_trace[1]["error_type"] is None

    second_trace = result.second_assistant_meta["routing_trace"]
    # The resumed turn should preserve the same resilience pattern as well.
    assert len(second_trace) == 2
    assert second_trace[0]["provider"] == Provider.OPENROUTER.value
    assert second_trace[0]["route_index"] == 0
    assert second_trace[0]["error_type"] == "TimeoutError"
    assert second_trace[1]["provider"] == Provider.GROQ.value
    assert second_trace[1]["route_index"] == 1
    assert second_trace[1]["error_type"] is None

    openrouter_requests = server.recorded_requests("POST", _OPENROUTER_PATH)
    groq_requests = server.recorded_requests("POST", _GROQ_PATH)
    assert len(openrouter_requests) == 2
    assert len(groq_requests) == 2
    openrouter_payloads = [
        json.loads(request.body.decode("utf-8")) for request in openrouter_requests
    ]
    groq_payloads = [
        json.loads(request.body.decode("utf-8")) for request in groq_requests
    ]
    assert all(isinstance(payload.get("model"), str) for payload in groq_payloads)
    assert all(isinstance(payload.get("model"), str) for payload in openrouter_payloads)


# =============================================================================
# Tests
# =============================================================================


def test_session_resume_preserves_timeout_fallback_metadata() -> None:
    """Verify saved sessions keep timeout-fallback assistant metadata."""
    with ScriptedHTTPServer(port=_PORT, routes=session_resilience_routes()) as server:
        # First run the recover-save-resume scenario once.
        result = run_pipeline(server_base_url=server.base_url)
        # Then prove the saved assistant metadata preserved both fallback traces.
        assert_pipeline_result(result, server=server)


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the session-resilience demo flow for manual execution."""
    console.demo_intro(__doc__)
    with ScriptedHTTPServer(port=_PORT, routes=session_resilience_routes()) as server:
        # Run the same resilience flow the test validates.
        result = run_pipeline(server_base_url=server.base_url)
        assert_pipeline_result(result, server=server)

    console.demo_step(
        "What Happened",
        "The session survived timeout-driven fallback, was saved, and "
        "still resumed with the right routing history.",
        details=[
            f"Final output: {result.output_text}",
            f"Saved history length: {result.saved_history_length}",
        ],
    )
    first_trace = result.first_assistant_meta["routing_trace"]
    second_trace = result.second_assistant_meta["routing_trace"]
    openrouter_hits = server.request_count("POST", _OPENROUTER_PATH)
    groq_hits = server.request_count("POST", _GROQ_PATH)
    console.demo_step(
        "Routing Evidence",
        "Both assistant turns show the same timeout-then-fallback "
        "pattern, which proves the saved session preserved the right "
        "metadata.",
        details=[
            f"First routing trace: {first_trace}",
            f"Second routing trace: {second_trace}",
            f"Server hits: openrouter={openrouter_hits}, groq={groq_hits}",
        ],
    )
    console.demo_outcome(
        "This passed because resilience behavior did not get lost "
        "when the session was saved and resumed later."
    )


if __name__ == "__main__":
    main()
# %%
