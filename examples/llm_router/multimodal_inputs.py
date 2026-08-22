"""Multimodal inputs
=================

Use the public file, image, local-video, and remote-video input shapes against
real providers.
"""
# %%

from __future__ import annotations

from pathlib import Path

from PIL import Image
from pydantic import BaseModel

from llm_router import (
    FileSchema,
    LLMRouter,
    Model,
    Provider,
    RouterProfile,
    VideoSchema,
    VideoUrlSchema,
)


def _example_dir() -> Path:
    """Return the example source directory for direct and gallery execution."""
    cwd = Path.cwd()
    if (cwd / "example_document.pdf").is_file():
        return cwd
    return cwd / "examples" / "llm_router"


EXAMPLE_DIR = _example_dir()


class PDFDigest(BaseModel):
    """Structured PDF result used by the example."""

    title: str
    abstract_one_sentence: str


class VideoObservation(BaseModel):
    """Structured video result used by the example."""

    action: str
    location: str


def main() -> None:
    """Run all live multimodal requests."""
    media_router = LLMRouter(
        RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.AISTUDIO),
        temperature=0.0,
        seed=42,
    )

    pdf = FileSchema(
        path=str(EXAMPLE_DIR / "example_document.pdf"),
        mime_type="application/pdf",
    )
    pdf_response = media_router.query(
        [
            "Read this paper and extract its title and a one-sentence abstract.",
            pdf,
        ],
        response_schema=PDFDigest,
    )
    print("PDF:")
    print(
        PDFDigest.model_validate_json(pdf_response.output_text).model_dump_json(
            indent=2
        )
    )

    with Image.open(EXAMPLE_DIR / "example_image.png") as source_image:
        image = source_image.convert("RGB").copy()
    image_response = media_router.query(
        ["Describe this image in one short sentence.", image]
    )
    print("\nIMAGE:")
    print(image_response.output_text)

    local_video = VideoSchema(path=str(EXAMPLE_DIR / "example_video.mp4"), fps=1)
    local_video_response = media_router.query(
        ["Describe the main action and location in this clip.", local_video],
        response_schema=VideoObservation,
    )
    print("\nLOCAL VIDEO:")
    print(
        VideoObservation.model_validate_json(
            local_video_response.output_text
        ).model_dump_json(indent=2)
    )

    remote_video = VideoUrlSchema(
        url="https://www.youtube.com/shorts/QUxqvF0pyGw",
        fps=1,
    )
    remote_video_response = media_router.query(
        ["Describe the main action and location in this video.", remote_video],
        response_schema=VideoObservation,
    )
    print("\nREMOTE VIDEO:")
    print(
        VideoObservation.model_validate_json(
            remote_video_response.output_text
        ).model_dump_json(indent=2)
    )


# %%
if __name__ == "__main__":
    main()
