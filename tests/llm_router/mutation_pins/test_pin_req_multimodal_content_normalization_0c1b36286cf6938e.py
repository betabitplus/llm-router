# mutation-pin: REQ_MULTIMODAL_CONTENT_NORMALIZATION 0c1b36286cf6938e
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest

from llm_router._internal.capabilities.content import normalize_content

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_MULTIMODAL_CONTENT_NORMALIZATION[revision==2]")
@pytest.mark.parametrize(
    "value",
    [
        pytest.param(b"", id="empty-bytes"),
        pytest.param(bytearray(b""), id="empty-bytearray"),
        pytest.param(b"payload", id="nonempty-bytes"),
    ],
)
def test_bytes_like_content_is_rejected_locally(value: object) -> None:
    with pytest.raises(TypeError, match=r"Unsupported message content"):
        normalize_content(value)
