# %%
"""LLM Router e2e: Gemini WebAPI structured-output recovery.

Why:
    Verifies that the public Gemini WebAPI structured-output path repairs an
    invalid first response locally and fails cleanly when repair attempts are
    exhausted.

Covers:
    Area: Gemini WebAPI structured-output path
    Behavior: local validation repair loop, terminal repair failure
    Interface: `LLMRouter(RouterProfile(...))`, `query(...)`

Checks:
    If the recoverable invalid-response branch runs, then the worker completes
    successfully.
    If repair succeeds on the second attempt, then the final output parses as the
    expected `TicketSummary`.
    If local repair actually runs, then the generate endpoint sees exactly 2 hits.
    If repair prompting is injected correctly, then the second request includes the
    previous response, a schema-failure marker, and the concrete incident values.
    If repair prompting carries concrete validation guidance, then the second request
    mentions required-or-schema rules, min-length or min-items constraints, `severity`,
    and `tags`.
    If repeated invalid responses exhaust recovery, then the worker ends in a clean
    failure result with public `ProviderError`.
    If recovery exhaustion really stops at the configured limit, then the generate
    endpoint sees exactly 3 hits.

Notes:
    This scenario is hermetic by construction because it talks only to a local
    scripted HTTP server and patches only external SDK modules in an isolated
    subprocess rather than changing library code.

Examples:
    Run manually:
        uv run python -m \
            tests.llm_router.e2e.provider_retries_and_output_repair.test_gemini_webapi_structured_recovery_pipeline

    Run as test:
        pytest \
            tests/llm_router/e2e/provider_retries_and_output_repair/test_gemini_webapi_structured_recovery_pipeline.py
"""

from __future__ import annotations

import json
from urllib.parse import unquote_plus

import pytest
from pydantic import BaseModel, Field

from tests.llm_router.support.assertions import parse_json_object
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.retry import (
    gemini_webapi_batch_path,
    gemini_webapi_batch_response,
    gemini_webapi_generate_path,
    gemini_webapi_google_path,
    gemini_webapi_init_path,
    gemini_webapi_init_response,
    gemini_webapi_stream_response,
)
from tests.llm_router.support.workers.structured_recovery import (
    StructuredRecoveryWorkerResult,
    run_structured_recovery_worker,
)
from py_lib_tooling import console

pytestmark = [
    pytest.mark.e2e_behavior,
    pytest.mark.cap_structured,
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
_CASE = "gemini_webapi"
_RECOVERY_JSON = {
    "incident_id": "INC-2048",
    "severity": "SEV2",
    "tags": ["db", "api"],
}
_INVALID_JSON = json.dumps({"incident_id": "INC-2048"})
_RECOVERY_TEXT = json.dumps(_RECOVERY_JSON)


# =============================================================================
# Helpers
# =============================================================================


class TicketSummary(BaseModel):
    """Structured output used by this recovery scenario."""

    incident_id: str
    severity: str = Field(min_length=4)
    tags: list[str] = Field(min_length=2, max_length=2)


def _bootstrap_routes() -> dict[tuple[str, str], list[ScriptedResponse]]:
    """Build shared bootstrap routes required by gemini_webapi."""
    return {
        ("GET", _GOOGLE_PATH): [ScriptedResponse(status_code=200, body=b"ok")],
        ("GET", _INIT_PATH): [
            ScriptedResponse(status_code=200, body=gemini_webapi_init_response())
        ],
        ("POST", _BATCH_PATH): [
            ScriptedResponse(status_code=200, body=gemini_webapi_batch_response())
        ],
    }


def recovery_routes() -> dict[tuple[str, str], list[ScriptedResponse]]:
    """Build scripted routes for one invalid answer followed by a valid repair."""
    return {
        **_bootstrap_routes(),
        ("POST", _GENERATE_PATH): [
            ScriptedResponse(
                status_code=200,
                body=gemini_webapi_stream_response(text=_INVALID_JSON),
            ),
            ScriptedResponse(
                status_code=200,
                body=gemini_webapi_stream_response(text=_RECOVERY_TEXT),
            ),
        ],
    }


def exhausted_routes() -> dict[tuple[str, str], list[ScriptedResponse]]:
    """Build scripted routes for repeated invalid structured responses."""
    invalid = ScriptedResponse(
        status_code=200,
        body=gemini_webapi_stream_response(text=_INVALID_JSON),
    )
    return {
        **_bootstrap_routes(),
        ("POST", _GENERATE_PATH): [invalid, invalid, invalid],
    }


def _second_request_text(server: ScriptedHTTPServer) -> str:
    """Return the second recorded Gemini generate request body as text."""
    requests = server.recorded_requests("POST", _GENERATE_PATH)
    raw = requests[1].body.decode("utf-8", errors="ignore")
    return unquote_plus(raw)


# =============================================================================
# Pipeline
# =============================================================================


def run_recovery_pipeline(*, server_base_url: str) -> StructuredRecoveryWorkerResult:
    """Run the structured recovery scenario."""
    # This worker path isolates one invalid answer followed by one repair attempt.
    return run_structured_recovery_worker(
        case=_CASE,
        scenario="recovery",
        server_base_url=server_base_url,
    )


def run_exhausted_pipeline(*, server_base_url: str) -> StructuredRecoveryWorkerResult:
    """Run the structured recovery exhaustion scenario."""
    # This worker path isolates the case where every repair attempt still fails.
    return run_structured_recovery_worker(
        case=_CASE,
        scenario="exhausted",
        server_base_url=server_base_url,
    )


# =============================================================================
# Assertions
# =============================================================================


def assert_recovery_response(
    result: StructuredRecoveryWorkerResult,
    *,
    server: ScriptedHTTPServer,
) -> None:
    """Assert local structured-output recovery succeeds on the second attempt."""
    # The worker must complete successfully for the recovery path.
    assert result.returncode == 0
    assert result.ok is True, result.stderr or result.error_message
    parsed = TicketSummary.model_validate(parse_json_object(result.output_text))
    # The final repaired output must match the exact structured object we expect.
    assert parsed == TicketSummary.model_validate(_RECOVERY_JSON)
    # Two generate hits prove there was one invalid attempt and one repair attempt.
    assert server.request_count("POST", _GENERATE_PATH) == 2
    second_request_text = _second_request_text(server)
    # We inspect the second outbound request itself to prove the router injected
    # schema guidance instead of succeeding by luck.
    assert (
        "The previous response did not match the required schema."
        in second_request_text
    )
    assert "Previous response" in second_request_text
    assert "incident_id" in second_request_text
    assert "INC-2048" in second_request_text

    # Prove the repair prompt included concrete validation guidance, not only a
    # generic marker. These tokens are derived from the schema constraints used
    # by this scenario (min_length/min_items and the required fields).
    lowered = second_request_text.lower()
    assert any(token in lowered for token in ("required", "schema"))
    assert any(token in lowered for token in ("minlength", "minitems"))
    assert "severity" in lowered
    assert "tags" in lowered


def assert_exhausted_error(
    result: StructuredRecoveryWorkerResult,
    *,
    server: ScriptedHTTPServer,
) -> None:
    """Assert repeated invalid structured output fails publicly."""
    # Exhaustion should still be a clean worker result, not a worker crash.
    assert result.returncode == 0
    assert result.ok is False
    # The public failure should stay a provider error with a structured-output
    # specific message.
    assert result.error_type == "ProviderError"
    assert "Structured output validation failed" in (result.error_message or "")
    # Three hits prove the repair loop exhausted all configured attempts.
    assert server.request_count("POST", _GENERATE_PATH) == 3


# =============================================================================
# Tests
# =============================================================================


def test_invalid_response_recovers_on_second_attempt() -> None:
    """Verify Gemini WebAPI repairs invalid structured output on the next attempt."""
    with ScriptedHTTPServer(port=_PORT, routes=recovery_routes()) as server:
        # First run the recoverable invalid-output scenario.
        result = run_recovery_pipeline(server_base_url=server.base_url)
        # Then prove the second request carried repair guidance and succeeded.
        assert_recovery_response(result, server=server)


def test_repeated_invalid_responses_fail_cleanly() -> None:
    """Verify repeated invalid Gemini structured output fails cleanly."""
    with ScriptedHTTPServer(port=_PORT, routes=exhausted_routes()) as server:
        # Run the exhausted-repair branch once.
        result = run_exhausted_pipeline(server_base_url=server.base_url)
        # Then prove the public failure stayed explicit.
        assert_exhausted_error(result, server=server)


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the structured recovery demo flow for manual execution."""
    console.demo_intro(__doc__)
    with ScriptedHTTPServer(port=_PORT, routes=recovery_routes()) as server:
        # Show the recoverable branch first.
        recovery_result = run_recovery_pipeline(server_base_url=server.base_url)
        assert_recovery_response(recovery_result, server=server)
        parsed = TicketSummary.model_validate(
            parse_json_object(recovery_result.output_text)
        )
        second_request_text = _second_request_text(server)
        has_guidance = (
            "Previous response" in second_request_text
            and "INC-2048" in second_request_text
        )

        console.demo_step(
            "What Happened On The Recovery Path",
            "The first invalid structured answer was corrected on the next attempt.",
            details=[
                f"Generate hits: {server.request_count('POST', _GENERATE_PATH)}",
                f"Repair prompt included guidance: {has_guidance}",
            ],
        )
        console.print_json(parsed.model_dump(mode="json"))

    with ScriptedHTTPServer(port=_PORT, routes=exhausted_routes()) as server:
        # Then contrast it with the branch where repair runs out of chances.
        exhausted_result = run_exhausted_pipeline(server_base_url=server.base_url)
        assert_exhausted_error(exhausted_result, server=server)

        console.demo_step(
            "What Happened When Recovery Was Exhausted",
            "When every answer stayed invalid, the flow stopped with a "
            "clear public error.",
            details=[
                "Public error: "
                f"{exhausted_result.error_type}: {exhausted_result.error_message}",
                f"Generate hits: {server.request_count('POST', _GENERATE_PATH)}",
            ],
        )
    console.demo_outcome(
        "This passed because the structured-output path both repairs "
        "recoverable mistakes and fails clearly when repair is no "
        "longer possible."
    )


if __name__ == "__main__":
    main()
# %%
