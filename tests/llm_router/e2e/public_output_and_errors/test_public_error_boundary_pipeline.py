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

"""

from __future__ import annotations

import pytest

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
