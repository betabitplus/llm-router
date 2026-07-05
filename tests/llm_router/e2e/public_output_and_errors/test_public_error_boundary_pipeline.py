# %%
"""LLM Router e2e: public error boundary behavior.

Why:
    Verifies that distinct public failure categories stay distinct at the
    library boundary.

Covers:
    Area: public error contract
    Behavior: configuration failure, missing key failure, provider failure
    Interface: `LLMRouter(...)`, `query(...)`

Checks:
    If API keys are missing, then the worker ends in a clean failure result with
    `ApiKeyNotFoundError`.
    If the missing-key boundary stays specific, then the public message mentions
    `OPENROUTER_API_KEY_1`.
    If model configuration is invalid, then the worker ends in a clean failure result
    with `ConfigurationError`.
    If the invalid-model boundary stays specific, then the public message mentions
    `Unknown model`.
    If a provider returns an HTTP failure, then the worker ends in a clean failure
    result with `ProviderError`.
    If the provider boundary stays specific, then the public message includes `local bad
    request`.
    If the provider failure crosses the boundary exactly once, then the scripted server
    sees 1 request.

Notes:
    This scenario is hermetic by construction because it uses no network or a
    local scripted HTTP server only.

Examples:
    Run manually:
        uv run python -m \
            tests.llm_router.e2e.public_output_and_errors.test_public_error_boundary_pipeline

    Run as test:
        pytest \
            tests/llm_router/e2e/public_output_and_errors/test_public_error_boundary_pipeline.py
"""

from __future__ import annotations

import pytest
from py_lib_tooling import console

from llm_router import ApiKeyNotFoundError, ConfigurationError, ProviderError
from tests.llm_router.support.fault_server import ScriptedHTTPServer, ScriptedResponse
from tests.llm_router.support.workers.error_boundary import (
    ErrorBoundaryWorkerResult,
    run_error_boundary_inprocess,
)
from tests.llm_router.support.workers.retry import (
    openai_chat_path,
    openai_error_response,
)

pytestmark = [
    pytest.mark.e2e_contract,
    pytest.mark.cap_resilience,
    pytest.mark.hermetic,
]


# =============================================================================
# Scenario
# =============================================================================

_PORT = 0
_OPENAI_PATH = openai_chat_path()


# =============================================================================
# Helpers
# =============================================================================


def provider_error_routes() -> dict[tuple[str, str], list[ScriptedResponse]]:
    """Build the scripted non-retryable provider failure route."""
    return {
        ("POST", _OPENAI_PATH): [
            ScriptedResponse(
                status_code=400,
                headers={"Content-Type": "application/json"},
                body=openai_error_response(
                    status_code=400,
                    message="local bad request",
                ),
            )
        ]
    }


# =============================================================================
# Pipeline
# =============================================================================


def run_missing_api_key_pipeline() -> ErrorBoundaryWorkerResult:
    """Run the missing API key public-error scenario."""
    # This worker path stops before any provider call, which is exactly what we
    # want to verify for missing credentials.
    return run_error_boundary_inprocess(scenario="missing_api_key")


def run_invalid_model_pipeline() -> ErrorBoundaryWorkerResult:
    """Run the invalid-model public-error scenario."""
    # This path isolates configuration validation from provider behavior.
    return run_error_boundary_inprocess(scenario="invalid_model")


def run_provider_error_pipeline(*, server_base_url: str) -> ErrorBoundaryWorkerResult:
    """Run the provider-error public-error scenario."""
    # This path reaches a real provider-shaped failure so we can contrast it
    # with the configuration failures above.
    return run_error_boundary_inprocess(
        scenario="provider_error",
        server_base_url=server_base_url,
    )


# =============================================================================
# Assertions
# =============================================================================


def assert_error_result(
    result: ErrorBoundaryWorkerResult,
    *,
    error_type: str,
    message_fragment: str,
) -> None:
    """Assert one public error result."""
    # The worker should finish cleanly so we know the failure came from the
    # router boundary we wanted to exercise.
    assert result.returncode == 0
    assert result.ok is False

    # The exact public error class is the main contract under test here.
    assert result.error_type == error_type

    # The message fragment check keeps the failure specific instead of allowing
    # a generic error of the same type to pass.
    assert message_fragment in (result.error_message or "")


# =============================================================================
# Tests
# =============================================================================


def test_missing_api_key_raises_public_configuration_error() -> None:
    """Verify missing keys surface as ApiKeyNotFoundError."""
    # Run the credential-missing path exactly once.
    result = run_missing_api_key_pipeline()
    # Then prove the public failure category is key-related, not generic.
    assert_error_result(
        result,
        error_type=ApiKeyNotFoundError.__name__,
        message_fragment="OPENROUTER_API_KEY_1",
    )


def test_invalid_model_raises_public_configuration_error() -> None:
    """Verify invalid models surface as ConfigurationError."""
    # Run the invalid-configuration path exactly once.
    result = run_invalid_model_pipeline()
    # Then prove it stayed a configuration error instead of leaking as a provider error.
    assert_error_result(
        result,
        error_type=ConfigurationError.__name__,
        message_fragment="Unknown model",
    )


def test_provider_http_failure_raises_public_provider_error() -> None:
    """Verify provider HTTP failures surface as ProviderError."""
    with ScriptedHTTPServer(port=_PORT, routes=provider_error_routes()) as server:
        # This time we intentionally cross the provider boundary.
        result = run_provider_error_pipeline(server_base_url=server.base_url)

        # The helper proves the public category is now a provider error.
        assert_error_result(
            result,
            error_type=ProviderError.__name__,
            message_fragment="local bad request",
        )
        assert server.request_count("POST", _OPENAI_PATH) == 1


# =============================================================================
# Demo (Manual Execution)
# =============================================================================


def main() -> None:
    """Run the public-error-boundary demo flow for manual execution."""
    console.demo_intro(__doc__)
    # Show the configuration-side failures first so the reader sees that the
    # library can stop early before any provider call.
    missing_key_result = run_missing_api_key_pipeline()
    assert_error_result(
        missing_key_result,
        error_type=ApiKeyNotFoundError.__name__,
        message_fragment="OPENROUTER_API_KEY_1",
    )

    console.demo_step(
        "What Happened With Missing Credentials",
        "The library stopped early with a key-related public error "
        "instead of attempting a provider call.",
        details=[
            "Public error: "
            f"{missing_key_result.error_type}: {missing_key_result.error_message}"
        ],
    )

    # Then show a different configuration failure with a different public type.
    invalid_model_result = run_invalid_model_pipeline()
    assert_error_result(
        invalid_model_result,
        error_type=ConfigurationError.__name__,
        message_fragment="Unknown model",
    )

    console.demo_step(
        "What Happened With Invalid Configuration",
        "The library rejected an invalid model configuration as a "
        "configuration problem, not as a provider problem.",
        details=[
            "Public error: "
            f"{invalid_model_result.error_type}: {invalid_model_result.error_message}"
        ],
    )

    with ScriptedHTTPServer(port=_PORT, routes=provider_error_routes()) as server:
        # Finally, contrast those early failures with a genuine provider-side failure.
        provider_result = run_provider_error_pipeline(server_base_url=server.base_url)
        assert_error_result(
            provider_result,
            error_type=ProviderError.__name__,
            message_fragment="local bad request",
        )

        console.demo_step(
            "What Happened With A Real Provider Failure",
            "A provider-side HTTP failure crossed the boundary as a provider "
            "error, which keeps it distinct from configuration issues.",
            details=[
                "Public error: "
                f"{provider_result.error_type}: {provider_result.error_message}",
                f"Server hits: {server.request_count('POST', _OPENAI_PATH)}",
            ],
        )
    console.demo_outcome(
        "This passed because the public API kept the three failure "
        "categories separate, which is exactly what downstream callers need."
    )


if __name__ == "__main__":
    main()
# %%
