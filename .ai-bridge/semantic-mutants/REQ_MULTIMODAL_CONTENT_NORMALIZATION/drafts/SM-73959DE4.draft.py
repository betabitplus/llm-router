# semantic-mutant: SM-73959DE4
from __future__ import annotations

import pytest

from llm_router._internal.capabilities.content import normalize_content

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_MULTIMODAL_CONTENT_NORMALIZATION[revision==2]")
def test_normalize_content_rejects_raw_bytes() -> None:
    with pytest.raises(TypeError, match=r"Unsupported message content: bytes\."):
        normalize_content(b"unsupported binary content")
