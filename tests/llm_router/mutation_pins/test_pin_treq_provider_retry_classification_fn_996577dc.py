# mutation-pin: TREQ_PROVIDER_RETRY_CLASSIFICATION FN-996577DC
# pinned-by: delegate, one pin for 4 pins of classify_status_code
# kills: 2f11d5445216910c 5a829211adec3347 77d6a6e9eef042e8 f49ab970d70faf89
from __future__ import annotations

import pytest

from llm_router._internal.providers.retry import (
    RetryClassification,
    RetryDecision,
    classify_status_code,
)

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_PROVIDER_RETRY_CLASSIFICATION[revision==1]")
def test_status_classification_semantics() -> None:
    retryable = classify_status_code(429)
    assert isinstance(retryable, RetryDecision)
    assert retryable.classification == RetryClassification.RETRYABLE
    assert retryable.reason == "retryable_status"
    assert retryable.status_code == 429

    server = classify_status_code(599)
    assert isinstance(server, RetryDecision)
    assert server.classification == RetryClassification.RETRYABLE
    assert server.reason == "server_status"
    assert server.status_code == 599

    other = classify_status_code(418)
    assert isinstance(other, RetryDecision)
    assert other.classification == RetryClassification.NON_RETRYABLE
    assert other.reason == "status_not_retryable"
    assert other.status_code == 418
