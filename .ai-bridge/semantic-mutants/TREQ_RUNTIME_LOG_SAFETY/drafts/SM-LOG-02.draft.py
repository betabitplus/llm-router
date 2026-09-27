# semantic-mutant: SM-LOG-02
"""Draft test for SM-LOG-02: the log context names the key by its id, never by its value, for every id."""

from __future__ import annotations

import pytest

from llm_router import Model, Provider
from llm_router._internal.providers.base import ProviderCredential, ProviderRequest

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_RUNTIME_LOG_SAFETY[revision==2]")
@pytest.mark.parametrize("key_id", [0, 1, 7])
def test_log_context_never_carries_the_credential(key_id: int) -> None:
    credential = "protected-credential-fixture"
    request = ProviderRequest(
        request_id="req-draft",
        provider=Provider.OPENROUTER,
        model=Model.DEEPSEEK_V3,
        provider_model="provider-model",
        credential=ProviderCredential(key_id=key_id, env_var=f"OPENROUTER_API_KEY_{key_id}", value=credential),
        messages=[],
    )

    context = request.log_context()

    assert context["key_id"] == key_id
    assert credential not in repr(context)
