# mutation-pin: TREQ_QWENCHAT_ADAPTER_BOUNDARY aeeb7e44dc927403
# pinned-by: claude-opus-5-5
from __future__ import annotations

import json
import typing

import pytest

from llm_router import Model, Provider
from llm_router._internal.capabilities.content import normalize_content
from llm_router._internal.providers.base import ProviderCredential, ProviderRequest
from llm_router._internal.providers.qwenchat import QwenChatAdapter

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("TREQ_QWENCHAT_ADAPTER_BOUNDARY[revision==1]")
def test_qwenchat_adapter_execute_disables_trust_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_kwargs: dict[str, typing.Any] = {}

    class FakeResponse:
        status_code = 200
        text = json.dumps(
            {
                "id": "chat-test-id",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "test answer",
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "total_tokens": 15,
                },
            }
        )

    class FakeClient:
        def __init__(self, *_args: typing.Any, **kwargs: typing.Any) -> None:
            captured_kwargs.update(kwargs)

        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, *_args: typing.Any) -> None:
            pass

        def post(self, *_args: typing.Any, **_kwargs: typing.Any) -> FakeResponse:
            return FakeResponse()

    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:1")
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:1")
    monkeypatch.setenv("ALL_PROXY", "http://127.0.0.1:1")
    monkeypatch.setattr(
        "llm_router._internal.providers.qwenchat.httpx.Client",
        FakeClient,
    )

    adapter = QwenChatAdapter(base_url="http://127.0.0.1:8000/api")
    request = ProviderRequest(
        request_id="req-boundary-1",
        provider=Provider.QWENCHAT,
        model=Model.QWEN_MAX_LATEST,
        provider_model="qwen-max-latest",
        credential=ProviderCredential(
            key_id=1,
            env_var="TEST_VAR",
            value="value",
        ),
        messages=[normalize_content("test message")],
    )

    result = adapter.execute(request)

    assert captured_kwargs.get("trust_env") is False
    assert result.output_text == "test answer"
