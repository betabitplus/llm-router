# mutation-pin: REQ_MULTIMODAL_CONTENT_NORMALIZATION 4e35b24fc276e4ad
# pinned-by: claude-opus-5-5
from __future__ import annotations

import pytest
from PIL import Image

from llm_router._internal.capabilities.content import MediaPart, normalize_content
from llm_router._internal.capabilities.media import ImageMedia

pytestmark = pytest.mark.verification_kind("unit")

_MAX_IMAGE_DIMENSION = 16384


@pytest.mark.verifies("REQ_MULTIMODAL_CONTENT_NORMALIZATION[revision==2]")
def test_image_at_max_dimension_boundary_normalizes() -> None:
    image = Image.new("RGB", (_MAX_IMAGE_DIMENSION, 10))

    normalized = normalize_content([image])

    part = next(iter(normalized.parts))
    assert isinstance(part, MediaPart)
    media = part.media
    assert isinstance(media, ImageMedia)
    assert media.kind == "image"
    assert media.width == _MAX_IMAGE_DIMENSION
    assert media.height == 10
    assert media.mode == "RGB"


@pytest.mark.verifies("REQ_MULTIMODAL_CONTENT_NORMALIZATION[revision==2]")
def test_image_above_max_dimension_is_rejected_locally() -> None:
    image = Image.new("RGB", (_MAX_IMAGE_DIMENSION + 1, 10))

    with pytest.raises(ValueError, match=r"too large"):
        normalize_content([image])
