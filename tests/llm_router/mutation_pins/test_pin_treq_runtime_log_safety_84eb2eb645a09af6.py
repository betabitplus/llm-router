# mutation-pin: TREQ_RUNTIME_LOG_SAFETY 84eb2eb645a09af6
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router import Model, Provider
from llm_router._internal.providers.base import ProviderFailure

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_RUNTIME_LOG_SAFETY[revision==2]")
@pytest.mark.parametrize("status_code", [0, 429, 503])
def test_provider_failure_with_status_code_reports_only_status(
    status_code: int,
) -> None:
    value = "untrusted-provider-failure-content"
    failure = ProviderFailure(
        provider=Provider.GEMINI_WEBAPI,
        model=Model.LLAMA_11B_VISION,
        message=value,
        retryable=False,
        status_code=status_code,
    )

    expected = f"Provider request failed with status code {status_code}."
    assert failure.message == expected
    assert str(failure) == expected
    assert value not in failure.message
    assert value not in str(failure)
