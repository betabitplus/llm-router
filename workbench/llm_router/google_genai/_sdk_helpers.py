"""Internal Google GenAI workbench SDK helpers.

Why:
    Keeps repeated client creation, parsed-output handling, and usage snapshots
    in one place so the Google GenAI workbench scripts stay focused on one SDK
    seam each.

When to use:
    Import from Google GenAI workbench scripts that make live SDK requests and
    want compact evidence from the native response object.
"""

from __future__ import annotations

import os
from typing import Any, cast

from google import genai
from pydantic import BaseModel


def build_client() -> genai.Client:
    """Build one live Google GenAI client from the local API key."""
    return genai.Client(api_key=os.environ["GOOGLE_API_KEY_1"])


def parsed_response_dict(response: object) -> dict[str, Any]:
    """Return structured parsed output as a plain JSON-ready dict."""
    parsed = getattr(response, "parsed", None)
    if isinstance(parsed, BaseModel):
        return parsed.model_dump(mode="json")
    if isinstance(parsed, dict):
        return cast("dict[str, Any]", parsed)

    msg = "The live response did not expose parsed structured output."
    raise TypeError(msg)


def response_text(response: object) -> str:
    """Return response text as a stripped string."""
    return str(getattr(response, "text", "") or "").strip()


def usage_snapshot(response: object) -> dict[str, int] | None:
    """Return a compact usage summary when the SDK exposed usage metadata."""
    usage = getattr(response, "usage_metadata", None)
    if usage is None:
        return None

    return {
        "input_tokens": int(getattr(usage, "prompt_token_count", 0) or 0),
        "output_tokens": int(getattr(usage, "candidates_token_count", 0) or 0),
        "total_tokens": int(getattr(usage, "total_token_count", 0) or 0),
    }
