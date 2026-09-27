# semantic-mutant: SM-LOG-01
"""Draft test for SM-LOG-01: no provider argument, whatever its name, enters the safe log context."""

from __future__ import annotations

import pytest

from llm_router import Model, Provider
from llm_router._internal.providers.base import ProviderCredential, ProviderRequest

pytestmark = pytest.mark.verification_kind("unit")

SAFE_FIELDS = {"request_id", "provider", "model", "key_id", "route_index"}


@pytest.mark.verifies("TREQ_RUNTIME_LOG_SAFETY[revision==2]")
@pytest.mark.parametrize("kwargs", [{}, {"debug": True}, {"verbose": "1"}, {"trace": 1, "custom_payload": "x"}])
def test_log_context_carries_no_provider_argument(kwargs: dict[str, object]) -> None:
    request = ProviderRequest(
        request_id="req-draft",
        provider=Provider.OPENROUTER,
        model=Model.DEEPSEEK_V3,
        provider_model="provider-model-private-detail",
        credential=ProviderCredential(key_id=1, env_var="OPENROUTER_API_KEY_1", value="protected-credential-fixture"),
        messages=[],
        kwargs=kwargs,
    )

    context = request.log_context()

    assert set(context) <= SAFE_FIELDS
    assert "protected-credential-fixture" not in repr(context)
