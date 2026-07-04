"""Property-based tests for provider SDK wrapping invariants.

Why:
    Protects the public provider-input wrappers through many generated valid
    inputs and a few explicit boundary examples.

How:
    Exercises only the supported top-level schema wrappers so provider-facing
    input semantics stay stable even if private adapter code evolves.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from hypothesis import given, strategies as st
from PIL import Image
from pydantic import BaseModel, ConfigDict

from llm_router import FileSchema, ImageSchema, VideoSchema, VideoUrlSchema

# =============================================================================
# Strategies
# =============================================================================


_SAFE_TEXT = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789_-",
    min_size=1,
    max_size=12,
)
_ALLOWED_IMAGE_MODES = st.sampled_from(["RGB", "RGBA", "L", "LA"])


class _ImageEnvelope(BaseModel):
    """Small validation harness for the public `ImageSchema` alias."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    image: ImageSchema


# =============================================================================
# Properties
# =============================================================================


@given(
    filename=_SAFE_TEXT,
    data=st.binary(max_size=128),
    mime_type=st.one_of(st.none(), st.sampled_from(["text/plain", "application/pdf"])),
)
def test_file_schema_accepts_existing_files(
    *,
    filename: str,
    data: bytes,
    mime_type: str | None,
) -> None:
    """`FileSchema` should preserve valid existing-file inputs."""
    with tempfile.TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / f"{filename}.bin"
        path.write_bytes(data)

        # The schema should act like a validating wrapper around the caller's
        # file intent, not a transformer that changes the meaning of the path.
        schema = FileSchema(path=str(path), mime_type=mime_type)

        assert Path(schema.path) == path
        assert schema.mime_type == mime_type


@given(
    filename=_SAFE_TEXT,
    data=st.binary(max_size=256),
    fps=st.integers(min_value=1, max_value=5),
    start_offset=st.one_of(st.none(), st.integers(min_value=0, max_value=20)),
    end_offset=st.one_of(st.none(), st.integers(min_value=0, max_value=20)),
)
def test_video_schema_accepts_existing_files(
    *,
    filename: str,
    data: bytes,
    fps: int,
    start_offset: int | None,
    end_offset: int | None,
) -> None:
    """`VideoSchema` should preserve valid local-file inputs."""
    with tempfile.TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / f"{filename}.mp4"
        path.write_bytes(data)

        # The public video wrapper should preserve the caller-visible hints as
        # long as the underlying file boundary is valid.
        schema = VideoSchema(
            path=str(path),
            fps=fps,
            start_offset=start_offset,
            end_offset=end_offset,
        )

        assert Path(schema.path) == path
        assert schema.fps == fps
        assert schema.start_offset == start_offset
        assert schema.end_offset == end_offset


@given(
    host=_SAFE_TEXT,
    path_segments=st.lists(_SAFE_TEXT, min_size=1, max_size=3),
    fps=st.integers(min_value=1, max_value=5),
    start_offset=st.one_of(st.none(), st.integers(min_value=0, max_value=20)),
    end_offset=st.one_of(st.none(), st.integers(min_value=0, max_value=20)),
)
def test_video_url_schema_accepts_absolute_urls(
    *,
    host: str,
    path_segments: list[str],
    fps: int,
    start_offset: int | None,
    end_offset: int | None,
) -> None:
    """`VideoUrlSchema` should preserve valid absolute URL inputs."""
    url = f"https://{host}.example/{'/'.join(path_segments)}"

    # This property deliberately stays narrow: one well-formed absolute URL
    # should round-trip through the public validator without semantic changes.
    schema = VideoUrlSchema(
        url=url,
        fps=fps,
        start_offset=start_offset,
        end_offset=end_offset,
    )

    assert schema.url == url
    assert schema.fps == fps
    assert schema.start_offset == start_offset
    assert schema.end_offset == end_offset


@given(
    mode=_ALLOWED_IMAGE_MODES,
    width=st.integers(min_value=10, max_value=128),
    height=st.integers(min_value=10, max_value=128),
)
def test_image_schema_accepts_allowed_images_unchanged(
    *,
    mode: str,
    width: int,
    height: int,
) -> None:
    """`ImageSchema` should accept caller-owned images inside public bounds."""
    # The image alias is intentionally lightweight: if the caller already has a
    # valid Pillow image, validation should preserve that object and only guard
    # the public size/mode boundary.
    image = Image.new(mode, (width, height))

    validated = _ImageEnvelope(image=image).image

    assert validated is image
    assert validated.mode == mode
    assert validated.size == (width, height)


# =============================================================================
# Tests
# =============================================================================


def test_file_schema_rejects_missing_files(tmp_path: Path) -> None:
    """Missing file paths should fail validation at the public boundary."""
    # This is kept as a named example instead of a generated property because
    # the negative rule is simple and easier to read as one concrete boundary.
    with pytest.raises(ValueError, match="File path does not exist"):
        FileSchema(path=str(tmp_path / "missing.bin"))


def test_image_schema_rejects_images_that_are_too_small() -> None:
    """Images below the documented minimum dimensions should fail fast."""
    # This is clearer as a concrete edge example than as a generated property:
    # the boundary itself matters more than a large family of negative inputs.
    image = Image.new("RGB", (9, 10))

    with pytest.raises(ValueError, match="too small"):
        _ImageEnvelope(image=image)


def test_image_schema_rejects_images_that_are_too_large() -> None:
    """Images above the documented maximum dimensions should fail fast."""
    image = Image.new("RGB", (16385, 10))

    with pytest.raises(ValueError, match="too large"):
        _ImageEnvelope(image=image)


def test_image_schema_rejects_unsupported_modes() -> None:
    """Unsupported Pillow modes should not cross the public image boundary."""
    image = Image.new("CMYK", (10, 10))

    with pytest.raises(ValueError, match="not supported"):
        _ImageEnvelope(image=image)
