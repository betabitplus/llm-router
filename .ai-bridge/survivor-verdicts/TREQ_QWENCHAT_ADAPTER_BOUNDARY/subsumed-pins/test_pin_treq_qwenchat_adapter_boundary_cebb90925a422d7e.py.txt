# mutation-pin: TREQ_QWENCHAT_ADAPTER_BOUNDARY cebb90925a422d7e
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router._api.types import Model, Provider
from llm_router._internal.capabilities.content import normalize_content
from llm_router._internal.providers.base import ProviderCredential, ProviderRequest
from llm_router._internal.providers.qwenchat import QwenChatAdapter

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.asyncio
@pytest.mark.verifies("TREQ_QWENCHAT_ADAPTER_BOUNDARY[revision==1]")
async def test_qwenchat_abuild_payload_preserves_kwargs() -> None:
    adapter = QwenChatAdapter(base_url="http://127.0.0.1:8000/api")
    credential = ProviderCredential(
        key_id=1,
        env_var="LOCAL_PROXY",
        value="proxy_value",
    )
    request = ProviderRequest(
        request_id="request-1",
        provider=Provider.QWENCHAT,
        model=Model.QWEN_MAX_LATEST,
        provider_model="qwen-max-latest",
        credential=credential,
        messages=[normalize_content("hello")],
        kwargs={"stream": True, "top_p": 0.8},
    )

    payload = await adapter.abuild_payload(request)

    assert payload["stream"] is True
    assert payload["top_p"] == 0.8
