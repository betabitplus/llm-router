"""llm_router-specific test data and output builders.

Why:
    Centralizes llm_router-owned media fixtures and manual-run output paths so
    e2e scripts reuse the same files and conventions.

When to use:
    Import from here when a test needs shared llm_router input assets or a
    repo-local output location for manual execution.

How:
    Keep reusable project fixtures here and return typed values that match the
    llm_router public API.

Examples:
    image = build_test_image()
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from llm_router import FileSchema, ImageSchema, VideoSchema, VideoUrlSchema
from tests.support.paths import get_repo_root, get_test_data_path

_DEFAULT_VIDEO_URL = "https://www.youtube.com/shorts/QUxqvF0pyGw"


def build_output_path(filename: str) -> Path:
    """Build a repo-local output path for manual e2e runs."""
    out_dir = get_repo_root() / "tests" / "llm_router" / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / filename


def get_llm_router_test_data_path(filename: str) -> Path:
    """Return a shared llm_router test-data file path."""
    path = get_test_data_path("llm_router") / filename
    if not path.exists():
        msg = f"Test data file not found: {path}"
        raise FileNotFoundError(msg)
    return path


def build_test_pdf_file(filename: str = "variative.pdf") -> FileSchema:
    """Build a shared PDF file attachment for e2e tests."""
    pdf_path = get_llm_router_test_data_path(filename)
    return FileSchema(path=str(pdf_path), mime_type="application/pdf")


def build_test_image(filename: str = "test_image.png") -> ImageSchema:
    """Build a shared image attachment for e2e tests."""
    image_path = get_llm_router_test_data_path(filename)
    return Image.open(image_path)


def build_test_video_file(filename: str = "jumper.mp4") -> VideoSchema:
    """Build a shared local video attachment for e2e tests."""
    video_path = get_llm_router_test_data_path(filename)
    return VideoSchema(path=str(video_path), fps=1)


def build_test_video_url(url: str = _DEFAULT_VIDEO_URL) -> VideoUrlSchema:
    """Build a shared remote video attachment for e2e tests."""
    return VideoUrlSchema(url=url, fps=1)
