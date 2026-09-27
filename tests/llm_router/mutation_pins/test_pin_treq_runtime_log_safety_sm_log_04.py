# mutation-pin: TREQ_RUNTIME_LOG_SAFETY SM-LOG-04
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router import Model, Provider
from llm_router._internal.providers.base import ProviderFailure

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_RUNTIME_LOG_SAFETY[revision==2]")
def test_provider_failure_without_status_code_discards_message() -> None:
    value = "untrusted-provider-failure-content"
    failure = ProviderFailure(
        provider=Provider.OPENROUTER,
        model=Model.DEEPSEEK_V3,
        message=value,
        retryable=False,
        status_code=None,
    )

    assert failure.message == "Provider request failed."
    assert value not in failure.message
    assert str(failure) == "Provider request failed."
    assert value not in str(failure)
