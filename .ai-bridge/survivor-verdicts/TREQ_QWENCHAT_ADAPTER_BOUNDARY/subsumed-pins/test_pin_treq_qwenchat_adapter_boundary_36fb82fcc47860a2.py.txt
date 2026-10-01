# mutation-pin: TREQ_QWENCHAT_ADAPTER_BOUNDARY 36fb82fcc47860a2
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router._api.types import Model, Provider
from llm_router._internal.capabilities.content import normalize_content
from llm_router._internal.providers.base import (
    ProviderCredential,
    ProviderRequest,
)
from llm_router._internal.providers.qwenchat import QwenChatAdapter

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.asyncio
@pytest.mark.verifies("TREQ_QWENCHAT_ADAPTER_BOUNDARY[revision==1]")
async def test_qwenchat_abuild_payload_int_temperature_coerced_to_float() -> None:
    adapter = QwenChatAdapter(base_url="http://127.0.0.1:8000")
    credential = ProviderCredential(
        key_id=1,
        env_var="ROUTER_VAR",
        value="auth-val",
    )
    request = ProviderRequest(
        request_id="req-int-temp",
        provider=Provider.QWENCHAT,
        model=Model.QWEN_MAX_LATEST,
        provider_model="qwen-max",
        credential=credential,
        messages=[normalize_content("hello")],
        temperature=1,
    )
    payload = await adapter.abuild_payload(request)
    assert payload["temperature"] == 1.0
    assert isinstance(payload["temperature"], float)
