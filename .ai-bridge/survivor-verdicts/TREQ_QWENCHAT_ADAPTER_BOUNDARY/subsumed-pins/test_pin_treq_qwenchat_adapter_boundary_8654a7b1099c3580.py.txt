# mutation-pin: TREQ_QWENCHAT_ADAPTER_BOUNDARY 8654a7b1099c3580
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
def test_qwenchat_transport_error_carries_normalized_failure_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport_error = qwenchat.httpx.ConnectError("proxy down at 127.0.0.1:8000")

    def fake_post(*_args: object, **_kwargs: object) -> object:
        raise transport_error

    monkeypatch.setattr(qwenchat.httpx.Client, "post", fake_post)

    original = qwenchat.transport_failure
    captured: list[object] = []

    def recording(**kwargs: object) -> object:
        failure = original(**kwargs)
        captured.append(failure)
        return failure

    monkeypatch.setattr(qwenchat, "transport_failure", recording)

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

    assert len(captured) == 1
    expected = captured[0].message
    assert expected
    assert str(exc_info.value).endswith(f"Reason: {expected}")
