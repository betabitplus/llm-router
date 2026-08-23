"""Send PDFs, images, and video
============================

Use the same ``query()`` API with a PDF, a Pillow image, a local video, and a remote
video URL. Each section keeps the input shape, request, and observed result together.
"""
# sphinx_gallery_tags = ["multimodal", "files", "video", "routing"]
# sphinx_gallery_thumbnail_path = "_static/gallery/multimodal.svg"

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

cwd = Path.cwd()
EXAMPLE_DIR = (
    cwd if (cwd / "example_document.pdf").is_file() else cwd / "examples/llm_router"
)


# %%
# Define small result shapes
# --------------------------
# Keep schemas focused on the fields the example wants to make visible.
class PDFDigest(BaseModel):
    """Small typed result for the PDF request."""

    title: str
    abstract_one_sentence: str


class VideoObservation(BaseModel):
    """Small typed result shared by local and remote video requests."""

    action: str
    location: str


# %%
# Create one multimodal router
# ----------------------------
# No special router mode is required. Media is supplied as part of the normal
# ``query()`` input sequence.
def build_router() -> LLMRouter:
    """Create the live router used by each media example."""
    return LLMRouter(
        RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.AISTUDIO),
        temperature=0.0,
        seed=42,
    )


# %%
# PDF → typed data
# ----------------
# The exact input is available as :download:`example_document.pdf
# <example_document.pdf>`. Wrap the path in ``FileSchema`` and place it beside the
# text instruction.
if __name__ == "__main__":
    router = build_router()
    pdf = FileSchema(
        path=str(EXAMPLE_DIR / "example_document.pdf"),
        mime_type="application/pdf",
    )
    pdf_response = router.query(
        ["Extract the title and summarize the abstract in one sentence.", pdf],
        response_schema=PDFDigest,
    )
    pdf_digest = PDFDigest.model_validate_json(pdf_response.output_text)

    print(f"title: {pdf_digest.title}")
    print(f"summary: {pdf_digest.abstract_one_sentence}")

# %%
# Pillow image → text
# -------------------
# This is the image sent in the next request:
#
# .. image:: example_image.png
#    :alt: Example image sent to the multimodal model
#    :width: 320px
#
# A normal ``PIL.Image.Image`` can be placed directly beside the text prompt.
if __name__ == "__main__":
    router = build_router()
    with Image.open(EXAMPLE_DIR / "example_image.png") as source_image:
        image = source_image.convert("RGB").copy()

    image_response = router.query(["Describe this image in one sentence.", image])
    print(f"description: {image_response.output_text.strip()}")

# %%
# Local video → typed observation
# -------------------------------
# The exact input is available as :download:`example_video.mp4
# <example_video.mp4>`. ``fps`` controls frame sampling before the provider request.
if __name__ == "__main__":
    router = build_router()
    local_video = VideoSchema(path=str(EXAMPLE_DIR / "example_video.mp4"), fps=1)
    local_response = router.query(
        ["Describe the main action and location in this clip.", local_video],
        response_schema=VideoObservation,
    )
    local_observation = VideoObservation.model_validate_json(local_response.output_text)

    print(f"action: {local_observation.action}")
    print(f"location: {local_observation.location}")

# %%
# Remote video URL → the same schema
# ----------------------------------
# ``VideoUrlSchema`` keeps the request shape the same when the media is remote. This
# example uses `this short video <https://www.youtube.com/shorts/QUxqvF0pyGw>`_.
if __name__ == "__main__":
    router = build_router()
    remote_video = VideoUrlSchema(
        url="https://www.youtube.com/shorts/QUxqvF0pyGw",
        fps=1,
    )
    remote_response = router.query(
        ["Describe the main action and location in this video.", remote_video],
        response_schema=VideoObservation,
    )
    remote_observation = VideoObservation.model_validate_json(
        remote_response.output_text
    )

    print(f"action: {remote_observation.action}")
    print(f"location: {remote_observation.location}")
