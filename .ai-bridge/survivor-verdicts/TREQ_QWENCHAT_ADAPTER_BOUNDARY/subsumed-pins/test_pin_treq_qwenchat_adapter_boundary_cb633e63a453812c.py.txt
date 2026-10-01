# mutation-pin: TREQ_QWENCHAT_ADAPTER_BOUNDARY cb633e63a453812c
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router import Model, Provider
from llm_router._internal.capabilities.content import normalize_content
from llm_router._internal.providers import qwenchat
from llm_router._internal.providers.base import ProviderCredential, ProviderRequest
from llm_router._internal.providers.qwenchat import QwenChatAdapter
from tests.llm_router.support.workers.retry import qwen_success_response

pytestmark = pytest.mark.verification_kind("unit")

CREATED: list[dict[str, object]] = []


class _Response:
    status_code = 200

    @property
    def text(self) -> str:
        return qwen_success_response(text="hi").decode()


class _FakeClient:
    def __init__(self, **kwargs: object) -> None:
        CREATED.append(dict(kwargs))

    def __enter__(self) -> _FakeClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.closed = exc_info is not None

    def post(self, url: str, **kwargs: object) -> _Response:
        self.last = (url, dict(kwargs))
        return _Response()


@pytest.mark.verifies("TREQ_QWENCHAT_ADAPTER_BOUNDARY[revision==1]")
def test_qwenchat_execute_passes_configured_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    CREATED.clear()
    monkeypatch.setattr(qwenchat.httpx, "Client", _FakeClient)
    request = ProviderRequest(
        request_id="req-1",
        provider=Provider.QWENCHAT,
        model=Model.QWEN_MAX_LATEST,
        provider_model="qwen-max-latest",
        credential=ProviderCredential(
            key_id=1, env_var="QWENCHAT_API_KEY_1", value="value"
        ),
        messages=[normalize_content("hello")],
    )
    adapter = QwenChatAdapter(base_url="http://proxy.local/api", timeout_seconds=123.0)
    adapter.execute(request)
    assert len(CREATED) == 1
    assert CREATED[0].get("timeout") == 123.0
