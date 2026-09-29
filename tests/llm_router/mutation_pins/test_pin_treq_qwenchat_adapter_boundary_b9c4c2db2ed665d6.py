# mutation-pin: TREQ_QWENCHAT_ADAPTER_BOUNDARY b9c4c2db2ed665d6
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router import Model, Provider
from llm_router._internal.capabilities.content import normalize_content
from llm_router._internal.providers.base import (
    ProviderCredential,
    ProviderRequest,
)
from llm_router._internal.providers.qwenchat import QwenChatAdapter

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.asyncio
@pytest.mark.verifies("TREQ_QWENCHAT_ADAPTER_BOUNDARY[revision==1]")
async def test_qwenchat_abuild_payload_carries_provider_model() -> None:
    adapter = QwenChatAdapter(base_url="http://127.0.0.1:8000/api")
    credential = ProviderCredential(
        key_id=1,
        env_var="BASE_URL",
        value="test_value",
    )
    request = ProviderRequest(
        request_id="req-test-model",
        provider=Provider.QWENCHAT,
        model=Model.QWEN_MAX_LATEST,
        provider_model="qwen-max-latest",
        credential=credential,
        messages=[normalize_content("Hello world")],
    )
    payload = await adapter.abuild_payload(request)
    assert payload["model"] == "qwen-max-latest"
    assert payload["stream"] is False
