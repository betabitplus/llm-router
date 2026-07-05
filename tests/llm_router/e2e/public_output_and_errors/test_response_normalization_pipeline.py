# %%
"""LLM Router e2e: response normalization parity.

Why:
    Verifies that distinct client implementations expose the same public
    response shape for equivalent successful requests.

Covers:
    Area: response normalization
    Behavior: normalized output text, usage, traces, and empty tool fields
    Interface: `LLMRouter(...).query(...)`

Checks:
    If the representative OpenAI-compatible route is normalized, then it succeeds with
    output text `parity-ok`.
    If the representative native Google route is normalized, then it succeeds with
    output text `parity-ok`.
    If OpenAI-compatible normalization is correct, then provider and model normalize to
    `openrouter` and `deepseek-chat-v3`.
    If native Google normalization is correct, then provider and model normalize to
    `google` and `gemini-3-flash`.
    If usage normalization is correct, then both results report the expected token
    counts.
    If simple-success routing normalization is correct, then each result keeps one
    successful route-0 trace.
    If empty tool fields are normalized correctly, then both results keep `tool_trace`
    and `tool_calls` as empty lists.
    If parity across client families holds, then both results expose identical public
    text and usage.
    If parity across routing metadata holds, then both normalized traces keep
    `wait_seconds` at `0.0`.

Notes:
    This scenario is hermetic by construction because it talks only to local
    scripted HTTP servers.

Examples:
    Run manually:
        uv run python -m \
            tests.llm_router.e2e.public_output_and_errors.test_response_normalization_pipeline

    Run as test:
        pytest \
            tests/llm_router/e2e/public_output_and_errors/test_response_normalization_pipeline.py
"""

from __future__ import annotations

import json

import pytest
from py_lib_tooling import console

from llm_router import Model
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.response_normalization import (
    ResponseNormalizationWorkerResult,
    run_response_normalization_dual_worker,
    run_response_normalization_worker,
)
from tests.llm_router.support.workers.retry import (
    google_generate_path,
    openai_chat_path,
    openai_success_response,
)

pytestmark = [
    pytest.mark.e2e_contract,
    pytest.mark.cap_resilience,
    pytest.mark.hermetic,
]


# =============================================================================
# Scenario
# =============================================================================

_OPENAI_PORT = 0
_GOOGLE_PORT = 0
_OPENAI_PATH = openai_chat_path()
_GOOGLE_PATH = google_generate_path(model=Model.GEMINI_3_FLASH)
_EXPECTED_TEXT = "parity-ok"
_EXPECTED_USAGE = {
    "input_tokens": 12,
    "output_tokens": 5,
    "total_tokens": 17,
}


# =============================================================================
# Helpers
# =============================================================================


def openai_routes() -> dict[tuple[str, str], list[ScriptedResponse]]:
    """Build the OpenAI-compatible parity route."""
    return {
        ("POST", _OPENAI_PATH): [
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=openai_success_response(text=_EXPECTED_TEXT),
            )
        ]
    }


def google_routes() -> dict[tuple[str, str], list[ScriptedResponse]]:
    """Build the Google parity route."""
    return {
        ("POST", _GOOGLE_PATH): [
            ScriptedResponse(
                status_code=200,
                headers={"Content-Type": "application/json"},
                body=google_parity_success_response(text=_EXPECTED_TEXT),
            )
        ]
    }


def google_parity_success_response(*, text: str) -> bytes:
    """Return a Google success payload with parity-matched usage counts."""
    return json.dumps(
        {
            "candidates": [
                {
                    "index": 0,
                    "content": {"role": "model", "parts": [{"text": text}]},
                    "finishReason": "STOP",
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 12,
                "candidatesTokenCount": 5,
                "totalTokenCount": 17,
            },
            "modelVersion": "local-model",
        }
    ).encode("utf-8")


# =============================================================================
# Pipeline
# =============================================================================


def run_openai_pipeline(*, server_base_url: str) -> ResponseNormalizationWorkerResult:
    """Run the OpenAI-compatible representative normalization scenario."""
    # This worker isolates one representative OpenAI-compatible success payload.
    return run_response_normalization_worker(
        case="openai",
        server_base_url=server_base_url,
    )


def run_google_pipeline(*, server_base_url: str) -> ResponseNormalizationWorkerResult:
    """Run the Google representative normalization scenario."""
    # This worker isolates one representative native Google success payload.
    return run_response_normalization_worker(
        case="google",
        server_base_url=server_base_url,
    )


def run_dual_pipeline(
    *,
    openai_server_base_url: str,
    google_server_base_url: str,
) -> tuple[ResponseNormalizationWorkerResult, ResponseNormalizationWorkerResult]:
    """Run both representative scenarios in one worker process."""
    return run_response_normalization_dual_worker(
        openai_server_base_url=openai_server_base_url,
        google_server_base_url=google_server_base_url,
    )


# =============================================================================
# Assertions
# =============================================================================


def assert_individual_result(
    result: ResponseNormalizationWorkerResult,
    *,
    expected_provider: str,
    expected_model: str,
) -> None:
    """Assert one normalized public response."""
    # The worker must complete successfully before we compare normalized fields.
    assert result.returncode == 0
    assert result.ok is True, result.stderr or result.error_message

    # The visible answer should survive normalization unchanged.
    assert result.output_text == _EXPECTED_TEXT

    # Provider and model should match the route that produced this response.
    assert result.provider == expected_provider
    assert result.model == expected_model

    # Usage normalization is one of the most important parity guarantees.
    assert result.usage == _EXPECTED_USAGE

    # A successful one-route call should keep a simple trace and empty tool
    # fields rather than injecting provider-specific extras.
    assert len(result.routing_trace) == 1
    assert result.routing_trace[0]["route_index"] == 0
    assert result.routing_trace[0]["error_type"] is None
    assert result.tool_trace == []
    assert result.tool_calls == []


def assert_parity(
    openai_result: ResponseNormalizationWorkerResult,
    google_result: ResponseNormalizationWorkerResult,
) -> None:
    """Assert equivalent public fields match across client families."""
    # The public text and usage should be identical even though the underlying
    # provider payloads are different.
    assert openai_result.output_text == google_result.output_text
    assert openai_result.usage == google_result.usage
    assert openai_result.tool_trace == google_result.tool_trace
    assert openai_result.tool_calls == google_result.tool_calls

    # Routing traces may carry provider-specific metadata, but the normalized
    # structural meaning of a simple successful call should still match.
    assert openai_result.routing_trace[0]["route_index"] == 0
    assert google_result.routing_trace[0]["route_index"] == 0
    assert openai_result.routing_trace[0]["wait_seconds"] == 0.0
    assert google_result.routing_trace[0]["wait_seconds"] == 0.0


# =============================================================================
# Tests
# =============================================================================


def test_representative_clients_normalize_to_the_same_public_shape() -> None:
    """Verify response normalization parity across representative clients."""
    with (
        ScriptedHTTPServer(port=_OPENAI_PORT, routes=openai_routes()) as openai_server,
        ScriptedHTTPServer(port=_GOOGLE_PORT, routes=google_routes()) as google_server,
    ):
        openai_result, google_result = run_dual_pipeline(
            openai_server_base_url=openai_server.base_url,
            google_server_base_url=google_server.base_url,
        )

    # Validate each result on its own before comparing them to each other.
    assert_individual_result(
        openai_result,
        expected_provider="openrouter",
        expected_model="deepseek-chat-v3",
    )
    assert_individual_result(
        google_result,
        expected_provider="google",
        expected_model="gemini-3-flash",
    )
    # Finally, prove both public responses converge to the same contract.
    assert_parity(openai_result, google_result)


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the response-normalization demo flow for manual execution."""
    console.demo_intro(__doc__)
    with ScriptedHTTPServer(port=_OPENAI_PORT, routes=openai_routes()) as openai_server:
        # Run the first representative client.
        openai_result = run_openai_pipeline(server_base_url=openai_server.base_url)

    with ScriptedHTTPServer(port=_GOOGLE_PORT, routes=google_routes()) as google_server:
        # Then run the second representative client.
        google_result = run_google_pipeline(server_base_url=google_server.base_url)

    assert_individual_result(
        openai_result,
        expected_provider="openrouter",
        expected_model="deepseek-chat-v3",
    )
    assert_individual_result(
        google_result,
        expected_provider="google",
        expected_model="gemini-3-flash",
    )
    assert_parity(openai_result, google_result)

    console.demo_step(
        "What Happened",
        "Two different client families produced the same public-shaped "
        "response for the same kind of successful request.",
        details=[
            "OpenAI-compatible: "
            f"provider={openai_result.provider}, "
            f"model={openai_result.model}, "
            f"output={openai_result.output_text}, "
            f"usage={openai_result.usage}",
            "Google GenAI: "
            f"provider={google_result.provider}, "
            f"model={google_result.model}, "
            f"output={google_result.output_text}, "
            f"usage={google_result.usage}",
            "OpenAI-compatible routing/tool fields: "
            f"{openai_result.routing_trace}, "
            f"{openai_result.tool_trace}, "
            f"{openai_result.tool_calls}",
            "Google routing/tool fields: "
            f"{google_result.routing_trace}, "
            f"{google_result.tool_trace}, "
            f"{google_result.tool_calls}",
        ],
    )
    console.demo_outcome(
        "This passed because the library normalized both providers "
        "into the same public contract instead of leaking "
        "backend-specific differences."
    )


if __name__ == "__main__":
    main()
# %%
