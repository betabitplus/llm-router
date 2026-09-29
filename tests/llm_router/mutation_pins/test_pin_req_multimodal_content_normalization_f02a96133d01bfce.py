# mutation-pin: REQ_MULTIMODAL_CONTENT_NORMALIZATION f02a96133d01bfce
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router import ChatMessage
from llm_router._internal.capabilities.content import (
    TextPart,
    normalize_chat_message,
    normalize_content,
)

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_MULTIMODAL_CONTENT_NORMALIZATION[revision==2]")
def test_plain_string_content_normalizes_to_single_ordered_text_part() -> None:
    value = "hello from a plain string message"

    normalized = normalize_content(value, role="assistant")

    assert normalized.role == "assistant"
    assert normalized.parts == (TextPart(kind="text", text=value),)
    assert normalized.meta == {}


@pytest.mark.verifies("REQ_MULTIMODAL_CONTENT_NORMALIZATION[revision==2]")
def test_chat_message_with_string_part_preserves_role_and_metadata() -> None:
    value = "single ordered greeting"
    message = ChatMessage(
        role="user",
        parts=(value,),
        meta={"trace_id": "abc-123"},
    )

    normalized = normalize_chat_message(message)

    assert normalized.role == "user"
    assert normalized.parts == (TextPart(kind="text", text=value),)
    assert normalized.meta == {"trace_id": "abc-123"}
    assert normalized.meta is not message.meta
