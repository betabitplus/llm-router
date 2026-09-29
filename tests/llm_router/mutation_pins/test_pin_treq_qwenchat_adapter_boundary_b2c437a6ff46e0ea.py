# mutation-pin: TREQ_QWENCHAT_ADAPTER_BOUNDARY b2c437a6ff46e0ea
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router import Model, Provider
from llm_router._internal.capabilities.content import normalize_content
from llm_router._internal.providers.base import ProviderCredential, ProviderRequest
from llm_router._internal.providers.qwenchat import QwenChatAdapter

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_QWENCHAT_ADAPTER_BOUNDARY[revision==1]")
def test_qwenchat_payload_seed_is_coerced_to_int() -> None:
    request = ProviderRequest(
        request_id="req-1",
        provider=Provider.QWENCHAT,
        model=Model.QWEN_MAX_LATEST,
        provider_model="qwen-max-latest",
        credential=ProviderCredential(
            key_id=1,
            env_var="QWENCHAT_API_KEY_1",
            value="value",
        ),
        messages=[normalize_content("hello")],
        temperature=0.0,
        seed=42.7,
    )
    adapter = QwenChatAdapter(base_url="https://example.com")

    payload = adapter.build_payload(request)

    assert payload["seed"] == 42
    assert isinstance(payload["seed"], int)
