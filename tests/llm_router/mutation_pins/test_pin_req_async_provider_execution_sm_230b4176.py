# mutation-pin: REQ_ASYNC_PROVIDER_EXECUTION SM-230B4176
# pinned-by: claude-opus-5-5
from __future__ import annotations

import asyncio
from typing import Any

import pytest

from llm_router import LLMRouter, Model, Provider, RouterProfile

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_ASYNC_PROVIDER_EXECUTION[revision==1]")
def test_async_route_settings_receive_dict_schema_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = "mock-provider-auth-12345"
    monkeypatch.setenv("NVIDIA_API_KEY", value)

    router = LLMRouter(
        RouterProfile(model=Model.DEEPSEEK_V4_FLASH, provider=Provider.NVIDIA)
    )
    runtime = getattr(router, "_runtime", router)
    schema = {
        "type": "object",
        "properties": {"answer": {"type": "string"}},
        "required": ["answer"],
    }
    seen: list[dict[str, Any]] = []
    original = runtime._settings_for_route

    def spy(*args: Any, **kwargs: Any) -> Any:
        seen.append(dict(kwargs["call_overrides"]))
        return original(*args, **kwargs)

    def stop(*_args: Any, **_kwargs: Any) -> Any:
        msg = "stop before network"
        raise RuntimeError(msg)

    monkeypatch.setattr(runtime, "_settings_for_route", spy)
    monkeypatch.setattr(runtime, "_prepare_request", stop)

    with pytest.raises(RuntimeError, match=r"stop before network"):
        asyncio.run(router.aquery("give an answer", response_schema=schema))

    assert seen
    for overrides in seen:
        assert overrides.get("response_schema") == schema
