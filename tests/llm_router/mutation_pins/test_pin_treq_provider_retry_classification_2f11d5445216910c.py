# mutation-pin: TREQ_PROVIDER_RETRY_CLASSIFICATION 2f11d5445216910c
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router._internal.providers.retry import (
    RetryClassification,
    classify_status_code,
)

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_PROVIDER_RETRY_CLASSIFICATION[revision==1]")
def test_status_codes_outside_explicit_sets_use_server_error_boundary() -> None:
    server_error_decision = classify_status_code(599)
    assert server_error_decision.classification == RetryClassification.RETRYABLE
    assert server_error_decision.reason == "server_status"

    unclassified_decision = classify_status_code(418)
    assert unclassified_decision.classification == RetryClassification.NON_RETRYABLE
    assert unclassified_decision.reason == "status_not_retryable"
