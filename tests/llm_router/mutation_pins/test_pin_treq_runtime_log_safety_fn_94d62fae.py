# mutation-pin: TREQ_RUNTIME_LOG_SAFETY FN-94D62FAE
# pinned-by: delegate, one pin for 2 pins of ProviderFailure.__post_init__
# kills: 84eb2eb645a09af6 SM-LOG-04
from __future__ import annotations

import pytest

from llm_router import Model, Provider
from llm_router._internal.providers.base import ProviderFailure

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_RUNTIME_LOG_SAFETY[revision==2]")
@pytest.mark.parametrize("status_code", [None, 0, 429, 503])
def test_provider_failure_message_is_bounded_and_safe(
    status_code: int | None,
) -> None:
    value = "untrusted-provider-failure-content"
    failure = ProviderFailure(
        provider=Provider.OPENROUTER,
        model=Model.DEEPSEEK_V3,
        message=value,
        retryable=False,
        status_code=status_code,
    )

    if status_code is None:
        expected = "Provider request failed."
    else:
        expected = f"Provider request failed with status code {status_code}."
    assert failure.message == expected
    assert str(failure) == expected
    assert value not in failure.message
    assert value not in str(failure)
