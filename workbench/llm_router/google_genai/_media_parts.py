# %%
"""Google GenAI workbench media-part helpers.

Why:
    Keeps the small native SDK part builders in one place so the media scripts
    stay focused on one feature instead of repeated part construction.

When to use:
    Import from Google GenAI workbench scripts that need PDF, local-video, or
    remote-video parts.
"""

from __future__ import annotations

from pathlib import Path

from google.genai import types


def build_pdf_part(path: Path) -> types.Part:
    """Build the inline PDF blob shape used by the adapter."""
    return types.Part(
        inline_data=types.Blob(
            data=path.read_bytes(),
            mime_type="application/pdf",
        )
    )


def build_video_file_part(path: Path) -> types.Part:
    """Build the inline local-video blob plus metadata shape."""
    return types.Part(
        inline_data=types.Blob(
            data=path.read_bytes(),
            mime_type="video/mp4",
        ),
        video_metadata=types.VideoMetadata(fps=1),
    )


def build_video_url_part(url: str) -> types.Part:
    """Build the remote video URL plus metadata shape."""
    return types.Part(
        file_data=types.FileData(file_uri=url),
        video_metadata=types.VideoMetadata(fps=1),
    )
