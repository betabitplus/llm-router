# mutation-pin: TREQ_RUNTIME_LOG_SAFETY SM-LOG-01
# pinned-by: claude-opus-5-5
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
def test_provider_request_log_context_excludes_debug_kwargs(
    route_index: int | None,
) -> None:
    sentinel = "sentinel-argument-payload"
    request = ProviderRequest(
        request_id="req-test-log-safety",
        provider=Provider.OPENROUTER,
        model=Model.DEEPSEEK_V3,
        provider_model="deepseek/deepseek-chat",
        credential=ProviderCredential(
            key_id=1,
            env_var="OPENROUTER_API_KEY_1",
            value="fixture-credential-value",
        ),
        messages=(),
        kwargs={"debug": True, "sentinel": sentinel},
        route_index=route_index,
    )

    context = request.log_context()

    expected_keys = {"request_id", "provider", "model", "key_id"}
    if route_index is not None:
        expected_keys.add("route_index")

    assert set(context) == expected_keys
    assert "kwargs" not in context
    assert sentinel not in context
    assert sentinel not in repr(context)
