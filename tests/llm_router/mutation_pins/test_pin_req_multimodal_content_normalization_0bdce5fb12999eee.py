# mutation-pin: REQ_MULTIMODAL_CONTENT_NORMALIZATION 0bdce5fb12999eee
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest
from PIL import Image

from llm_router._internal.capabilities.content import MediaPart, normalize_content
from llm_router._internal.capabilities.media import _MIN_IMAGE_DIMENSION, ImageMedia

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_MULTIMODAL_CONTENT_NORMALIZATION[revision==2]")
def test_image_at_minimum_dimension_is_accepted() -> None:
    image = Image.new("RGB", (_MIN_IMAGE_DIMENSION, _MIN_IMAGE_DIMENSION))

    normalized = normalize_content([image])

    part = next(iter(normalized.parts))
    assert isinstance(part, MediaPart)
    media = part.media
    assert isinstance(media, ImageMedia)
    assert media.width == _MIN_IMAGE_DIMENSION
    assert media.height == _MIN_IMAGE_DIMENSION
    assert media.mode == "RGB"


@pytest.mark.verifies("REQ_MULTIMODAL_CONTENT_NORMALIZATION[revision==2]")
def test_image_one_pixel_narrower_than_minimum_is_rejected() -> None:
    image = Image.new("RGB", (_MIN_IMAGE_DIMENSION - 1, _MIN_IMAGE_DIMENSION))

    with pytest.raises(ValueError, match=r"too small"):
        normalize_content([image])
