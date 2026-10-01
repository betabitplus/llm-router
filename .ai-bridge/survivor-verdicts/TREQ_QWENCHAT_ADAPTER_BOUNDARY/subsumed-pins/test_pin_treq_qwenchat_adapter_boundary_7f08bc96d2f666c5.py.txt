# mutation-pin: TREQ_QWENCHAT_ADAPTER_BOUNDARY 7f08bc96d2f666c5
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router import Model, Provider
from llm_router._internal.providers.base import ProviderCredential, ProviderRequest
from llm_router._internal.providers.qwenchat import QwenChatAdapter

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_QWENCHAT_ADAPTER_BOUNDARY[revision==1]")
def test_qwenchat_build_payload_preserves_request_kwargs() -> None:
    adapter = QwenChatAdapter(
        base_url="http://localhost:8000/v1", timeout_seconds=600.0
    )
    request = ProviderRequest(
        request_id="req-qwenchat-extra-kwargs-1",
        provider=Provider.QWENCHAT,
        model=Model.QWEN_MAX_LATEST,
        provider_model="qwen-max",
        credential=ProviderCredential(
            key_id=1,
            env_var="DASHSCOPE_API_KEY",
            value="test-api-key",
        ),
        messages=(),
        kwargs={"extra": "value"},
    )

    payload = adapter.build_payload(request=request)

    assert payload["model"] == "qwen-max"
    assert payload["messages"] == []
    assert payload["stream"] is False
    assert payload["extra"] == "value"
