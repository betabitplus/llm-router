# mutation-pin: REQ_MULTIMODAL_CONTENT_NORMALIZATION SM-227845E0
# pinned-by: claude-opus-5-5
from __future__ import annotations

from dataclasses import dataclass

import pytest

from llm_router._internal.capabilities.media import describe_media

pytestmark = pytest.mark.verification_kind("unit")


@dataclass
class PathLike:
    path: str
    mime_type: str | None = None


@pytest.mark.verifies("REQ_MULTIMODAL_CONTENT_NORMALIZATION[revision==2]")
def test_unsupported_media_object_with_path_attribute_is_rejected() -> None:
    value = PathLike(path="clip.bin", mime_type="application/octet-stream")

    with pytest.raises(TypeError, match=r"Unsupported media value: PathLike"):
        describe_media(value)
