# mutation-pin: TREQ_QWENCHAT_ADAPTER_BOUNDARY d553c778448d4a6c
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router._api.errors import ProviderError
from llm_router._api.types import Model, Provider
from llm_router._internal.capabilities.content import normalize_content
from llm_router._internal.providers import qwenchat
from llm_router._internal.providers.base import ProviderCredential, ProviderRequest
from llm_router._internal.providers.qwenchat import QwenChatAdapter

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_QWENCHAT_ADAPTER_BOUNDARY[revision==1]")
def test_qwenchat_transport_failure_raises_provider_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport_error = qwenchat.httpx.ConnectError("connection refused")

    def fake_post(*_args: object, **_kwargs: object) -> object:
        raise transport_error

    monkeypatch.setattr(qwenchat.httpx.Client, "post", fake_post)

    adapter = QwenChatAdapter(base_url="http://127.0.0.1:8000")
    request = ProviderRequest(
        request_id="req-1",
        provider=Provider.QWENCHAT,
        model=Model.QWEN_MAX_LATEST,
        provider_model="qwen-max-latest",
        credential=ProviderCredential(
            key_id=1,
            env_var="QWEN_VALUE",
            value="value",
        ),
        messages=[normalize_content("ping")],
    )

    with pytest.raises(ProviderError, match=r".+") as exc_info:
        adapter.execute(request)

    assert exc_info.value.provider == Provider.QWENCHAT
    assert exc_info.value.model == Model.QWEN_MAX_LATEST
    assert exc_info.value.__cause__ is transport_error
