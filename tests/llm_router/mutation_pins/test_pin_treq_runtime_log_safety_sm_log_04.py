# mutation-pin: TREQ_RUNTIME_LOG_SAFETY SM-LOG-04
# pinned-by: claude-opus-5-5: When status_code is None, the mutant adds the provider-supplied message to the public failure text. TREQ_RUNTIME_LOG_SAFETY explicitly forbids copying provider error text into public failure messages, so this change breaks the requirement.
"""Draft test for SM-LOG-04: a provider failure never carries the provider's text, with or without a status code."""

from __future__ import annotations

import pytest

from llm_router import Model, Provider
from llm_router._internal.providers.base import ProviderFailure

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_RUNTIME_LOG_SAFETY[revision==2]")
@pytest.mark.parametrize("status_code", [None, 400, 500])
def test_provider_failure_message_never_carries_provider_text(status_code: int | None) -> None:
    failure = ProviderFailure(
        provider=Provider.OPENROUTER,
        model=Model.DEEPSEEK_V3,
        message="protected-provider-text-fixture",
        retryable=False,
        status_code=status_code,
    )

    assert "protected-provider-text-fixture" not in failure.message
    assert "protected-provider-text-fixture" not in str(failure)
