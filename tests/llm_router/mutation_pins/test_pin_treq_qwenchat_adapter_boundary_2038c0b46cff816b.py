# mutation-pin: TREQ_QWENCHAT_ADAPTER_BOUNDARY 2038c0b46cff816b
# pinned-by: claude-opus-5-5: The mutant sets 'stream': True, which asks the QwenChat proxy for a streamed (SSE) reply. The adapter expects one complete JSON response, so this breaks the proxy HTTP behaviour and the normalized response semantics that TREQ_QWENCHAT_ADAPTER_BOUNDARY requires the adapter to preserve.
from __future__ import annotations

import pytest
from llm_router import Model, Provider
from llm_router._internal.capabilities.content import normalize_content
from llm_router._internal.providers.base import ProviderCredential, ProviderRequest
from llm_router._internal.providers.qwenchat import QwenChatAdapter

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_QWENCHAT_ADAPTER_BOUNDARY[revision==1]")
def test_qwenchat_build_payload_sets_stream_false_for_text_request() -> None:
    adapter = QwenChatAdapter(base_url="http://127.0.0.1:8000/v1", timeout_seconds=60.0)
    credential = ProviderCredential(
        key_id=1,
        env_var="QWEN_API_KEY",
        value="qwen-secret-key-12345",
    )
    request = ProviderRequest(
        request_id="req-qwen-stream-verification",
        provider=Provider.QWENCHAT,
        model=Model.QWEN_MAX_LATEST,
        provider_model="qwen-max",
        credential=credential,
        messages=[
            normalize_content(["Hello, summarize this text."]),
        ],
        kwargs={},
    )

    payload = adapter.build_payload(request=request)

    assert payload["stream"] is False
    assert payload["model"] == "qwen-max"
