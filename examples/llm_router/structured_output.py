"""Extract typed data
==================

Pass a Pydantic model as ``response_schema`` and turn free-form source text into a
validated Python object in one request.
"""
# sphinx_gallery_tags = ["structured-output", "routing", "pydantic"]
# sphinx_gallery_thumbnail_path = "_static/gallery/structured-output.svg"

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from llm_router import LLMRouter, Model


# %%
# Define the result shape
# -----------------------
# The schema is ordinary Pydantic: use the smallest shape that expresses the result
# your application actually needs.
class Incident(BaseModel):
    """Typed incident extracted from unstructured text."""

    incident_id: str
    service: str
    region: str
    status_code: int
    severity: Literal["low", "medium", "high"]


# %%
# Define the input and request the schema
# ---------------------------------------
# The important part is ``response_schema=Incident``. The router asks the provider
# for structured output; ``model_validate_json`` then gives you a normal typed
# object rather than an unvalidated string.
if __name__ == "__main__":
    source = (
        "Incident INC-204: Checkout API in eu-west-1 is returning HTTP 503. "
        "Severity is high."
    )
    router = LLMRouter(Model.GEMINI_FLASH, temperature=0.0, seed=42)
    response = router.query(
        ["Extract the incident details from this report.", source],
        response_schema=Incident,
    )
    incident = Incident.model_validate_json(response.output_text)

    print(incident.model_dump_json(indent=2))
