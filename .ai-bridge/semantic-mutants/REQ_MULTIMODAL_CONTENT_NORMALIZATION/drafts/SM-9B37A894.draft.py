# semantic-mutant: SM-9B37A894
from __future__ import annotations

import pytest
from llm_router._internal.capabilities.content import (
    TextPart,
    normalize_content,
)

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_MULTIMODAL_CONTENT_NORMALIZATION[revision==2]")
def test_normalize_content_preserves_caller_specified_role() -> None:
    normalized = normalize_content(
        "Please summarize the system status.",
        role="assistant",
    )

    assert normalized.role == "assistant"
    assert tuple(
        part.text for part in normalized.parts if isinstance(part, TextPart)
    ) == ("Please summarize the system status.",)
    assert normalized.meta == {}
