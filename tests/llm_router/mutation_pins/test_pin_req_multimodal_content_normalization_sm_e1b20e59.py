# mutation-pin: REQ_MULTIMODAL_CONTENT_NORMALIZATION SM-E1B20E59
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router._internal.capabilities.content import normalize_content

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_MULTIMODAL_CONTENT_NORMALIZATION[revision==2]")
def test_empty_text_part_is_preserved_in_caller_order() -> None:
    value = ["", "hello", ""]

    message = normalize_content(value)

    assert len(message.parts) == 3
    assert [part.text for part in message.parts] == ["", "hello", ""]
