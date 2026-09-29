# mutation-pin: REQ_MULTIMODAL_CONTENT_NORMALIZATION 03b3464429e96b31
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest
from PIL import Image

from llm_router._internal.capabilities.content import normalize_content

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_MULTIMODAL_CONTENT_NORMALIZATION[revision==2]")
def test_image_with_valid_width_and_short_height_is_rejected() -> None:
    value = [Image.new("RGB", (32, 0))]

    with pytest.raises(ValueError, match=r"too small"):
        normalize_content(value)
