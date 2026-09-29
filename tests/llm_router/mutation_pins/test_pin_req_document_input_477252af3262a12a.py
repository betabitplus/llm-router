# mutation-pin: REQ_DOCUMENT_INPUT 477252af3262a12a
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router import LLMRouter, Model, Provider, RouterProfile

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_DOCUMENT_INPUT[revision==1]")
def test_non_document_media_value_is_rejected_as_unsupported() -> None:
    router = LLMRouter(
        RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.GOOGLE),
        temperature=0.0,
        seed=42,
    )
    value = b"\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00"

    with pytest.raises(TypeError, match=r"Unsupported media value"):
        router.query(["Describe this.", value])
