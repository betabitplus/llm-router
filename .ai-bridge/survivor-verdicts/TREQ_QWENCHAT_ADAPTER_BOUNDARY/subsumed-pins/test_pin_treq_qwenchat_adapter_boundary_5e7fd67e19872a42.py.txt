# mutation-pin: TREQ_QWENCHAT_ADAPTER_BOUNDARY 5e7fd67e19872a42
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
async def test_qwenchat_abuild_payload_temperature_preserved() -> None:
    adapter = QwenChatAdapter(base_url="http://127.0.0.1:8000")
    credential = ProviderCredential(
        key_id=1,
        env_var="ROUTER_VAR",
        value="auth-val",
    )
    request_with_temp = ProviderRequest(
        request_id="req-temp",
        provider=Provider.QWENCHAT,
        model=Model.QWEN_MAX_LATEST,
        provider_model="qwen-max",
        credential=credential,
        messages=[normalize_content("hello")],
        temperature=0.3,
    )
    payload_with_temp = await adapter.abuild_payload(request_with_temp)
    assert payload_with_temp["temperature"] == 0.3
    assert isinstance(payload_with_temp["temperature"], float)

    request_none_temp = ProviderRequest(
        request_id="req-none",
        provider=Provider.QWENCHAT,
        model=Model.QWEN_MAX_LATEST,
        provider_model="qwen-max",
        credential=credential,
        messages=[normalize_content("hello")],
        temperature=None,
    )
    payload_none_temp = await adapter.abuild_payload(request_none_temp)
    assert "temperature" not in payload_none_temp
