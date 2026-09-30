# mutation-pin: REQ_ASYNC_PROVIDER_EXECUTION SM-230B4176
# pinned-by: claude-opus-5-5
from __future__ import annotations

import asyncio

import pytest

from llm_router import LLMRouter, Model, Provider, RouterProfile

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_ASYNC_PROVIDER_EXECUTION[revision==1]")
def test_async_call_dict_schema_override_reaches_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = "mock-provider-auth-12345"
    monkeypatch.setenv("NVIDIA_API_KEY", value)
    router = LLMRouter(
        RouterProfile(model=Model.DEEPSEEK_V4_FLASH, provider=Provider.NVIDIA)
    )
    bad_schema = {"type": 12345, "properties": [1, 2, 3]}
    with pytest.raises(Exception, match=r"(?i)schema"):
        asyncio.run(router.aquery("give an answer", response_schema=bad_schema))
