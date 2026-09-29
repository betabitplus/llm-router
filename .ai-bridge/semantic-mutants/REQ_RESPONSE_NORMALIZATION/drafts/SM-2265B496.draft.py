# semantic-mutant: SM-2265B496
from __future__ import annotations

import types

import pytest
from llm_router import Model, Provider
from llm_router._internal.providers.base import ProviderResult
from llm_router._internal.runtime.output import build_public_response

pytestmark = pytest.mark.verification_kind("unit")


def _result(data: dict) -> ProviderResult:
    return ProviderResult(
        data=data,
        provider=Provider.GOOGLE,
        model=Model.GEMINI_FLASH_LITE,
        provider_model="gemini-3.5-flash-lite",
        output_text="ok",
    )


@pytest.mark.verifies("REQ_RESPONSE_NORMALIZATION[revision==1]")
def test_provider_parsed_kept_and_structured_data_is_json_safe() -> None:
    supplied = build_public_response(
        _result({"parsed": {"city": "Paris"}}),
        structured_data={"city": "Berlin"},
    )
    assert supplied.data["parsed"] == {"city": "Paris"}

    missing = build_public_response(
        _result({}),
        structured_data=types.SimpleNamespace(),
    )
    assert missing.data["parsed"] == {
        "type": "SimpleNamespace",
        "preview": "namespace()",
    }
