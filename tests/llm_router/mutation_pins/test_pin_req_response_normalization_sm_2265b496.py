# mutation-pin: REQ_RESPONSE_NORMALIZATION SM-2265B496
# pinned-by: claude-opus-5-5
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

import llm_router

pytestmark = pytest.mark.verification_kind("unit")


def _build(data: dict, structured: object) -> object:
    output = llm_router._internal.runtime.output
    result = SimpleNamespace(
        data=data,
        provider=SimpleNamespace(value="google"),
        model=llm_router.Model.GEMINI_FLASH_LITE,
        output_text="hello",
        usage=None,
        tool_calls=(),
    )
    return output.build_public_response(result, structured_data=structured)


@pytest.mark.verifies("REQ_RESPONSE_NORMALIZATION[revision==1]")
def test_structured_parsed_is_json_safe_and_existing_parsed_kept() -> None:
    response = _build({}, SimpleNamespace())
    parsed = response.data["parsed"]
    assert parsed == {"type": "SimpleNamespace", "preview": "namespace()"}
    json.dumps(dict(response.data))

    kept = _build({"parsed": {"a": 1}}, SimpleNamespace())
    assert kept.data["parsed"] == {"a": 1}
