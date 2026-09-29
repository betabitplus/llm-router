# mutation-pin: REQ_RESPONSE_NORMALIZATION SM-7211CDB1
# pinned-by: claude-opus-5-5
from __future__ import annotations

import types

import pytest

import llm_router

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_RESPONSE_NORMALIZATION[revision==1]")
def test_explicit_empty_text_and_tool_calls_override_provider_values() -> None:
    call = llm_router.ToolCall(id="call-1", name="lookup", args={"q": "x"})
    result = types.SimpleNamespace(
        data={},
        usage=None,
        provider=types.SimpleNamespace(value="google"),
        model=types.SimpleNamespace(value="gemini-3.5-flash-lite"),
        output_text="raw provider text",
        tool_calls=(call,),
    )
    build = llm_router._internal.runtime.output.build_public_response
    response = build(result, output_text="", tool_calls=())
    assert response.output_text == ""
    assert response.tool_calls == []
