# mutation-pin: TREQ_QWENCHAT_ADAPTER_BOUNDARY 8fddc8d6682ad36b
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router import Model, Provider
from llm_router._internal.capabilities.content import normalize_content
from llm_router._internal.providers.base import ProviderCredential, ProviderRequest
from llm_router._internal.providers.qwenchat import QwenChatAdapter

pytestmark = pytest.mark.verification_kind("unit")


def _request(temperature: object) -> ProviderRequest:
    return ProviderRequest(
        request_id="req-1",
        provider=Provider.QWENCHAT,
        model=Model.QWEN_VL_32B,
        provider_model="qwen-vl-32b",
        credential=ProviderCredential(
            key_id=1,
            env_var="QWENCHAT_API_KEY_1",
            value="value",
        ),
        messages=[normalize_content("hello")],
        temperature=temperature,
    )


@pytest.mark.verifies("TREQ_QWENCHAT_ADAPTER_BOUNDARY[revision==1]")
def test_build_payload_coerces_temperature_to_float() -> None:
    adapter = QwenChatAdapter(base_url="https://example.com")
    as_int = adapter.build_payload(_request(1))
    assert as_int["temperature"] == 1.0
    assert isinstance(as_int["temperature"], float)
    as_text = adapter.build_payload(_request("0.5"))
    assert as_text["temperature"] == 0.5
    assert isinstance(as_text["temperature"], float)
    with pytest.raises(ValueError, match=r"."):
        adapter.build_payload(_request("not-a-number"))
