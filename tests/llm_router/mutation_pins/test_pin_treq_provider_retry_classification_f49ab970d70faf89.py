# mutation-pin: TREQ_PROVIDER_RETRY_CLASSIFICATION f49ab970d70faf89
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router._internal.providers.retry import (
    RetryClassification,
    RetryDecision,
    classify_status_code,
)

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_PROVIDER_RETRY_CLASSIFICATION[revision==1]")
def test_unmatched_sub_500_status_code_is_classified_as_non_retryable() -> None:
    decision = classify_status_code(418)

    assert isinstance(decision, RetryDecision)
    assert decision.classification == RetryClassification.NON_RETRYABLE
    assert decision.reason == "status_not_retryable"
    assert decision.status_code == 418
