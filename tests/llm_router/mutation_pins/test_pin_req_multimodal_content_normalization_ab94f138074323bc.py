# mutation-pin: REQ_MULTIMODAL_CONTENT_NORMALIZATION ab94f138074323bc
# pinned-by: claude-opus-5-5
"""Pin _validate_image checking both width and height against the max bound.

Regression for defect ab94f138074323bc, which drops the
`image.height > _MAX_IMAGE_DIMENSION` half of the max-size check, so an
image that is within the width bound but exceeds the max height is no
longer rejected before provider execution.
"""

from __future__ import annotations

import pytest
from PIL import Image

from llm_router._internal.capabilities.content import normalize_content

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_MULTIMODAL_CONTENT_NORMALIZATION[revision==2]")
def test_image_height_over_max_is_rejected_locally() -> None:
    # Width stays comfortably within bounds; only height exceeds the max
    # (16384, inferred from the project's own "16385 -> too large" example)
    # so this input only distinguishes the two checks when both are `or`ed.
    image = Image.new("RGB", (512, 16385))
    with pytest.raises(ValueError, match=r"too large"):
        normalize_content([image])
