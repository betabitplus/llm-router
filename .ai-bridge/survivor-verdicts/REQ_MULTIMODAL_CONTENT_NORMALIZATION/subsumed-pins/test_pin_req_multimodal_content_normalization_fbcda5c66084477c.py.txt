# mutation-pin: REQ_MULTIMODAL_CONTENT_NORMALIZATION fbcda5c66084477c
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router._internal.capabilities.content import TextPart, normalize_content

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_MULTIMODAL_CONTENT_NORMALIZATION[revision==2]")
def test_plain_string_content_normalizes_to_single_text_part() -> None:
    value = "control-plane heartbeat status ok"

    result = normalize_content(value)

    assert len(result.parts) == 1
    part = next(iter(result.parts))
    assert isinstance(part, TextPart)
    assert part.text == value
