# mutation-pin: REQ_MULTIMODAL_CONTENT_NORMALIZATION e9186235c6377e40
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest
from PIL import Image

import llm_router._internal.capabilities.media as media_module
from llm_router._internal.capabilities.content import MediaPart, normalize_content
from llm_router._internal.capabilities.media import ImageMedia

pytestmark = pytest.mark.verification_kind("unit")

MAX_DIMENSION = media_module._MAX_IMAGE_DIMENSION


@pytest.mark.verifies("REQ_MULTIMODAL_CONTENT_NORMALIZATION[revision==2]")
@pytest.mark.parametrize(
    ("height", "expect_error"),
    [
        pytest.param(MAX_DIMENSION, False, id="height-at-max-boundary"),
        pytest.param(MAX_DIMENSION + 1, True, id="height-over-max-boundary"),
    ],
)
def test_image_height_at_max_boundary(height: int, expect_error: bool) -> None:
    image = Image.new("RGB", (MAX_DIMENSION, height))

    if expect_error:
        with pytest.raises(ValueError, match=r"too large"):
            normalize_content([image])
        return

    normalized = normalize_content([image])
    part = next(iter(normalized.parts))

    assert isinstance(part, MediaPart)
    assert isinstance(part.media, ImageMedia)
    assert part.media.width == MAX_DIMENSION
    assert part.media.height == MAX_DIMENSION
    assert part.media.mode == "RGB"
