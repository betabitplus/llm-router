# mutation-pin: TREQ_PROVIDER_RETRY_CLASSIFICATION 5a829211adec3347
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router._internal.providers.retry import (
    RetryClassification,
    classify_status_code,
)

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_PROVIDER_RETRY_CLASSIFICATION[revision==1]")
def test_unlisted_5xx_status_code_is_retryable() -> None:
    decision = classify_status_code(599)

    assert decision is not None
    assert decision.classification == RetryClassification.RETRYABLE
    assert decision.reason == "server_status"
    assert decision.status_code == 599
