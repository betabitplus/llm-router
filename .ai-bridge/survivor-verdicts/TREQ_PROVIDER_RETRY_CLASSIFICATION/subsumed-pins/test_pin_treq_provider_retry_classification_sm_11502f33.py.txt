# mutation-pin: TREQ_PROVIDER_RETRY_CLASSIFICATION SM-11502F33
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router._internal.providers.retry import (
    RetryClassification,
    classify_exception,
)

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_PROVIDER_RETRY_CLASSIFICATION[revision==1]")
def test_transport_exception_subclass_is_retryable() -> None:
    decision = classify_exception(ConnectionResetError("reset by peer"))

    assert decision.classification is RetryClassification.RETRYABLE
    assert decision.reason == "transport_exception"
