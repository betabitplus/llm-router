# mutation-pin: TREQ_QWENCHAT_ADAPTER_BOUNDARY 4f1c2e37ad20c744
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
async def test_qwenchat_abuild_payload_disables_stream() -> None:
    credential = ProviderCredential(
        key_id=1,
        env_var="ENV_VAR",
        value="adapter_value",
    )
    request = ProviderRequest(
        request_id="req-1",
        provider=Provider.QWENCHAT,
        model=Model.QWEN_MAX_LATEST,
        provider_model="qwen-max-latest",
        credential=credential,
        messages=[normalize_content("Hello")],
    )
    adapter = QwenChatAdapter(base_url="http://127.0.0.1:1/api")

    payload = await adapter.abuild_payload(request)

    assert payload["stream"] is False
