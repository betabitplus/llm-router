# mutation-pin: TREQ_RUNTIME_LOG_SAFETY FN-12FC5C09
# pinned-by: delegate, one pin for 2 pins of ProviderRequest.log_context
# kills: SM-LOG-01 SM-LOG-02
from __future__ import annotations

import pytest

from llm_router import Model, Provider
from llm_router._internal.providers.base import (
    ProviderCredential,
    ProviderRequest,
)

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_RUNTIME_LOG_SAFETY[revision==2]")
@pytest.mark.parametrize("route_index", [None, 0])
@pytest.mark.parametrize("key_id", [0, 1])
def test_log_context_exposes_only_safe_fields(
    route_index: int | None, key_id: int
) -> None:
    sentinel = "sentinel-argument-payload"
    value = "protected-credential-fixture"
    request = ProviderRequest(
        request_id="req-test-log-safety",
        provider=Provider.OPENROUTER,
        model=Model.DEEPSEEK_V3,
        provider_model="deepseek/deepseek-chat",
        credential=ProviderCredential(
            key_id=key_id,
            env_var=f"OPENROUTER_API_KEY_{key_id}",
            value=value,
        ),
        messages=[],
        kwargs={"debug": True, "sentinel": sentinel},
        route_index=route_index,
    )

    context = request.log_context()

    expected_keys = {"request_id", "provider", "model", "key_id"}
    if route_index is not None:
        expected_keys.add("route_index")
    assert set(context) == expected_keys
    assert context["key_id"] == key_id
    assert "kwargs" not in context
    assert sentinel not in repr(context)
    assert value not in repr(context)
