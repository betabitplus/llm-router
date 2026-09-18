from __future__ import annotations

import pytest

from llm_router._internal.providers.retry import (
    classify_exception,
    classify_status_code,
)

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_PROVIDER_RETRY_CLASSIFICATION[revision==1]")
@pytest.mark.coverage_item("VC_PROVIDER_RETRY_STATUS_CLASSIFICATION")
def test_retryable_status_is_classified_from_status_semantics() -> None:
    decision = classify_status_code(503)

    assert (decision.retryable, decision.reason) == (True, "retryable_status")


@pytest.mark.verifies("TREQ_PROVIDER_RETRY_CLASSIFICATION[revision==1]")
@pytest.mark.coverage_item("VC_PROVIDER_RETRY_STATUS_CLASSIFICATION")
def test_permanent_status_is_classified_from_status_semantics() -> None:
    decision = classify_status_code(400)

    assert (decision.retryable, decision.reason) == (False, "caller_or_auth_status")


@pytest.mark.verifies("TREQ_PROVIDER_RETRY_CLASSIFICATION[revision==1]")
@pytest.mark.coverage_item("VC_PROVIDER_RETRY_EXCEPTION_CLASSIFICATION")
def test_transport_exception_type_is_retryable() -> None:
    decision = classify_exception(ConnectionError("gone"))

    assert (decision.retryable, decision.reason) == (True, "transport_exception")


@pytest.mark.verifies("TREQ_PROVIDER_RETRY_CLASSIFICATION[revision==1]")
@pytest.mark.coverage_item("VC_PROVIDER_RETRY_EXCEPTION_CLASSIFICATION")
def test_unrelated_exception_is_not_retryable_despite_retrylike_name_fragment() -> None:
    class ReadOnlyConfigurationError(RuntimeError):
        pass

    decision = classify_exception(ReadOnlyConfigurationError("timeout network"))

    assert (decision.retryable, decision.reason) == (
        False,
        "exception_not_retryable",
    )
