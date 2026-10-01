# mutation-pin: TREQ_PROVIDER_RETRY_CLASSIFICATION 77d6a6e9eef042e8
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router._internal.providers.retry import (
    RetryClassification,
    classify_status_code,
)

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_PROVIDER_RETRY_CLASSIFICATION[revision==1]")
def test_retryable_status_decision_echoes_input_status_code() -> None:
    status_code = 429

    decision = classify_status_code(status_code)

    assert decision.classification == RetryClassification.RETRYABLE
    assert decision.reason == "retryable_status"
    assert decision.status_code == status_code
