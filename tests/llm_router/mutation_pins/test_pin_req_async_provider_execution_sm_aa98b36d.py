# mutation-pin: REQ_ASYNC_PROVIDER_EXECUTION SM-AA98B36D
# pinned-by: claude-opus-5-5
from __future__ import annotations

import asyncio
from typing import Any

import pytest

from llm_router import LLMRouter, Model, Provider, RouterProfile

pytestmark = pytest.mark.verification_kind("unit")


class _Key:
    key_id = 1


class _Request:
    key = _Key()


@pytest.mark.verifies("REQ_ASYNC_PROVIDER_EXECUTION[revision==1]")
def test_async_success_passes_original_non_text_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = "mock-provider-auth-12345"
    monkeypatch.setenv("NVIDIA_API_KEY", value)
    router = LLMRouter(
        RouterProfile(model=Model.DEEPSEEK_V4_FLASH, provider=Provider.NVIDIA)
    )
    runtime = getattr(router, "_runtime", router)
    seen: list[object] = []
    final = object()

    def fake_prepare(*_a: Any, **_k: Any) -> tuple[Any, float]:
        return _Request(), 0.0

    async def fake_call(*_a: Any, **_k: Any) -> object:
        return object()

    def fake_complete(**kwargs: Any) -> object:
        seen.append(kwargs["content"])
        return final

    def noop(*_a: Any, **_k: Any) -> None:
        return None

    monkeypatch.setattr(runtime, "_prepare_request", fake_prepare)
    monkeypatch.setattr(runtime, "_call_async_with_timeout", fake_call)
    monkeypatch.setattr(runtime, "_complete_success", fake_complete)
    for name in (
        "_record_success",
        "_remember_fallback_success",
        "_log_attempt_started",
        "_log_attempt_succeeded",
    ):
        monkeypatch.setattr(runtime, name, noop)

    content = [
        {"type": "text", "text": "describe the image"},
        {"type": "image_url", "image_url": {"url": "https://example.com/a.png"}},
    ]
    result = asyncio.run(router.aquery(content))

    assert result is final
    assert len(seen) == 1
    assert seen[0] is content
    assert not isinstance(seen[0], str)
