"""Provider-neutral media normalization.

Why:
    Keeps public file, image, and video DTO interpretation out of provider
    adapters until an adapter must translate it to an SDK payload.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from PIL import Image

from llm_router._api.types import FileSchema, VideoSchema, VideoUrlSchema


@dataclass(frozen=True, slots=True)
class FileMedia:
    """Local file descriptor for adapter-owned upload or inline handling."""

    kind: Literal["file"]
    path: str
    mime_type: str | None


@dataclass(frozen=True, slots=True)
class ImageMedia:
    """In-memory image descriptor that does not serialize image bytes."""

    kind: Literal["image"]
    image: Image.Image
    width: int
    height: int
    mode: str


@dataclass(frozen=True, slots=True)
class VideoFileMedia:
    """Local video descriptor with public sampling hints."""

    kind: Literal["video_file"]
    path: str
    fps: int
    start_offset: int | None
    end_offset: int | None


@dataclass(frozen=True, slots=True)
class VideoUrlMedia:
    """Remote video descriptor with public sampling hints."""

    kind: Literal["video_url"]
    url: str
    fps: int
    start_offset: int | None
    end_offset: int | None


MediaDescriptor = FileMedia | ImageMedia | VideoFileMedia | VideoUrlMedia

_ALLOWED_IMAGE_MODES = frozenset({"RGB", "RGBA", "L", "LA", "P", "PA"})
_MIN_IMAGE_DIMENSION = 1
_MAX_IMAGE_DIMENSION = 16384


def describe_media(value: object) -> MediaDescriptor:
    """Return a provider-neutral media descriptor for a public media object."""
    if isinstance(value, FileSchema):
        return FileMedia(kind="file", path=value.path, mime_type=value.mime_type)
    if isinstance(value, Image.Image):
        _validate_image(value)
        return ImageMedia(
            kind="image",
            image=value,
            width=value.width,
            height=value.height,
            mode=value.mode,
        )
    if isinstance(value, VideoSchema):
        return VideoFileMedia(
            kind="video_file",
            path=value.path,
            fps=value.fps,
            start_offset=value.start_offset,
            end_offset=value.end_offset,
        )
    if isinstance(value, VideoUrlSchema):
        return VideoUrlMedia(
            kind="video_url",
            url=value.url,
            fps=value.fps,
            start_offset=value.start_offset,
            end_offset=value.end_offset,
        )

    msg = f"Unsupported media value: {type(value).__name__}."
    raise TypeError(msg)


def _validate_image(image: Image.Image) -> None:
    """Validate raw Pillow images before they enter normalized content."""
    if image.width < _MIN_IMAGE_DIMENSION or image.height < _MIN_IMAGE_DIMENSION:
        msg = (
            f"Image dimensions {image.width}x{image.height} are too small "
            f"(min {_MIN_IMAGE_DIMENSION}x{_MIN_IMAGE_DIMENSION})."
        )
        raise ValueError(msg)
    if image.width > _MAX_IMAGE_DIMENSION or image.height > _MAX_IMAGE_DIMENSION:
        msg = (
            f"Image dimensions {image.width}x{image.height} are too large "
            f"(max {_MAX_IMAGE_DIMENSION}x{_MAX_IMAGE_DIMENSION})."
        )
        raise ValueError(msg)
    if image.mode not in _ALLOWED_IMAGE_MODES:
        msg = f"Image mode {image.mode!r} is not supported."
        raise ValueError(msg)
