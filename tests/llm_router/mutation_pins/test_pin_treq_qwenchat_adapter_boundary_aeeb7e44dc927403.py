# mutation-pin: TREQ_QWENCHAT_ADAPTER_BOUNDARY aeeb7e44dc927403
# pinned-by: claude-opus-5-5: This mutant is not equivalent. A test can set the process environment, and with trust_env=True, variables such as HTTP_PROXY, HTTPS_PROXY, ALL_PROXY, NO_PROXY, SSL_CERT_FILE and NETRC change where and how the adapter's upload and chat requests travel. TREQ_QWENCHAT_ADAPTER_BOUNDARY requires the adap
from __future__ import annotations

import dataclasses
import json
import typing

import pytest

from llm_router import Model, Provider
from llm_router._internal.capabilities.content import normalize_content
from llm_router._internal.providers.base import ProviderCredential, ProviderRequest
from llm_router._internal.providers.qwenchat import QwenChatAdapter
import llm_router._internal.providers.qwenchat
from tests.llm_router.support.workers.retry import qwen_success_response

pytestmark = pytest.mark.verification_kind("unit")


def _make_credential() -> typing.Any:
    if dataclasses.is_dataclass(ProviderCredential):
        kwargs: dict[str, typing.Any] = {}
        for f in dataclasses.fields(ProviderCredential):
            if f.name == "api_key":
                kwargs["api_key"] = "test-api-key"
            elif f.default is not dataclasses.MISSING:
                kwargs[f.name] = f.default
            elif f.default_factory is not dataclasses.MISSING:  # type: ignore[comparison-overlap]
                kwargs[f.name] = f.default_factory()
            else:
                kwargs[f.name] = "test-credential"
        try:
            return ProviderCredential(**kwargs)
        except Exception:
            pass
    try:
        return ProviderCredential(api_key="test-api-key")
    except Exception:
        try:
            return ProviderCredential()
        except Exception:
            return None


def _make_request() -> ProviderRequest:
    provider = getattr(Provider, "QWENCHAT", None)
    if provider is None:
        provider = getattr(Provider, "QWEN", None)
    if provider is None and hasattr(Provider, "__iter__"):
        provider = next(iter(Provider))  # type: ignore[call-overload]
    if provider is None:
        provider = "qwenchat"

    model = getattr(Model, "QWEN_MAX", None)
    if model is None:
        model = getattr(Model, "QWEN_PLUS", None)
    if model is None and hasattr(Model, "__iter__"):
        model = next(iter(Model))  # type: ignore[call-overload]
    if model is None:
        model = "qwen-max"

    provider_model = getattr(model, "value", str(model)) if model is not None else "qwen-max"

    base_kwargs: dict[str, typing.Any] = {
        "request_id": "test-req-boundary-001",
        "provider": provider,
        "model": model,
        "provider_model": provider_model,
        "messages": [normalize_content("hello")],
        "credential": _make_credential(),
        "kwargs": {},
        "temperature": None,
        "seed": None,
        "tool_registry": None,
        "tool_choice": None,
    }

    if dataclasses.is_dataclass(ProviderRequest):
        fields = {f.name: f for f in dataclasses.fields(ProviderRequest)}
        call_kwargs: dict[str, typing.Any] = {}
        for name, f in fields.items():
            if name in base_kwargs:
                call_kwargs[name] = base_kwargs[name]
            elif f.default is not dataclasses.MISSING:
                call_kwargs[name] = f.default
            elif f.default_factory is not dataclasses.MISSING:  # type: ignore[comparison-overlap]
                call_kwargs[name] = f.default_factory()
            else:
                call_kwargs[name] = None
        return ProviderRequest(**call_kwargs)

    try:
        return ProviderRequest(**base_kwargs)
    except Exception:
        return ProviderRequest(
            request_id="test-req-boundary-001",
            provider=provider,
            model=model,
            messages=[normalize_content("hello")],
        )


@pytest.mark.verifies("TREQ_QWENCHAT_ADAPTER_BOUNDARY[revision==1]")
def test_qwenchat_execute_disables_trust_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HTTP_PROXY", "http://unreachable.proxy.invalid:8080")
    monkeypatch.setenv("HTTPS_PROXY", "http://unreachable.proxy.invalid:8080")
    monkeypatch.setenv("ALL_PROXY", "http://unreachable.proxy.invalid:8080")

    captured_kwargs: list[dict[str, typing.Any]] = []

    class MockResponse:
        def __init__(self, status_code: int, text: str) -> None:
            self.status_code = status_code
            self.text = text

        def json(self) -> typing.Any:
            return json.loads(self.text)

    class MockClient:
        def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
            captured_kwargs.append(kwargs)

        def __enter__(self) -> MockClient:
            return self

        def __exit__(self, *args: typing.Any) -> None:
            pass

        def post(self, *args: typing.Any, **kwargs: typing.Any) -> MockResponse:
            resp_status = 200
            resp_text = json.dumps({
                "id": "chatcmpl-test",
                "object": "chat.completion",
                "created": 1700000000,
                "model": "qwen-max",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "Hello from mock proxy",
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "total_tokens": 15,
                },
            })
            try:
                sample = qwen_success_response()
                if hasattr(sample, "status_code"):
                    resp_status = sample.status_code
                elif hasattr(sample, "status"):
                    resp_status = sample.status
                if hasattr(sample, "text"):
                    resp_text = sample.text
                elif hasattr(sample, "body"):
                    b = sample.body
                    if isinstance(b, (bytes, bytearray)):
                        resp_text = b.decode("utf-8")
                    elif isinstance(b, str):
                        resp_text = b
                    elif isinstance(b, dict):
                        resp_text = json.dumps(b)
                elif isinstance(sample, str):
                    resp_text = sample
                elif isinstance(sample, dict):
                    resp_text = json.dumps(sample)
            except Exception:
                pass
            return MockResponse(resp_status, resp_text)

    monkeypatch.setattr(
        llm_router._internal.providers.qwenchat.httpx,
        "Client",
        MockClient,
    )

    adapter = QwenChatAdapter(base_url="http://127.0.0.1:8000")
    request = _make_request()

    result = adapter.execute(request)

    assert result is not None
    assert len(captured_kwargs) == 1
    assert captured_kwargs[0].get("trust_env") is False
