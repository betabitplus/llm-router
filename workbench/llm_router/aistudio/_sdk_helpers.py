"""Internal AI Studio workbench SDK helpers.

Why:
    Keeps repeated OpenAI-compatible client creation, response parsing, and
    image encoding in one place so the AI Studio workbench scripts stay focused
    on one provider seam each.

When to use:
    Import from AI Studio workbench scripts that exercise the non-video
    OpenAI-compatible endpoint.
"""

from __future__ import annotations

import base64
import json
import mimetypes
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import httpx
from openai import AsyncOpenAI, OpenAI

if TYPE_CHECKING:
    from openai.types.chat import ChatCompletion

_DEFAULT_OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
_AISTUDIO_PROVIDER_NAME = "AISTUDIO"


# ======================================================================================
# Runtime Configuration
# ======================================================================================


def provider_api_key_env(provider_name: str) -> str:
    """Build the conventional `<PROVIDER>_API_KEY_1` env var name."""
    return f"{provider_name}_API_KEY_1"


def openai_base_url() -> str:
    """Return the OpenAI-compatible AI Studio base URL for workbench runs."""
    override = os.getenv("WORKBENCH_AISTUDIO_OPENAI_BASE_URL")
    return override or _DEFAULT_OPENAI_BASE_URL


def api_key_env_name() -> str:
    """Return the preferred env var for live AI Studio workbench runs."""
    override = os.getenv("WORKBENCH_AISTUDIO_API_KEY_ENV")
    if override:
        return override
    if os.getenv("GOOGLE_API_KEY_1"):
        return "GOOGLE_API_KEY_1"
    return provider_api_key_env(_AISTUDIO_PROVIDER_NAME)


# ======================================================================================
# Client Builders
# ======================================================================================


def build_client() -> OpenAI:
    """Build one sync AI Studio OpenAI-compatible client."""
    return OpenAI(
        api_key=os.environ[api_key_env_name()],
        base_url=openai_base_url(),
        max_retries=0,
        http_client=httpx.Client(trust_env=False),
    )


def build_async_client() -> AsyncOpenAI:
    """Build one async AI Studio OpenAI-compatible client."""
    return AsyncOpenAI(
        api_key=os.environ[api_key_env_name()],
        base_url=openai_base_url(),
        max_retries=0,
        http_client=httpx.AsyncClient(trust_env=False),
    )


# ======================================================================================
# Small Payload Helpers
# ======================================================================================


def image_data_url(path: Path) -> str:
    """Convert a real image file into an inline data URL."""
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    payload = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{payload}"


# ======================================================================================
# Response Inspection
# ======================================================================================


def _assistant_content_text(response: ChatCompletion, *, context: str) -> str:
    """Return assistant message text and fail loudly when it is missing."""
    content = response.choices[0].message.content
    if not isinstance(content, str) or not content.strip():
        msg = f"The live response did not expose assistant {context} text."
        raise TypeError(msg)
    return content.strip()


def parse_message_json(response: ChatCompletion) -> dict[str, Any]:
    """Parse assistant JSON text and fail loudly if it is missing."""
    parsed = json.loads(_assistant_content_text(response, context="JSON"))
    if not isinstance(parsed, dict):
        msg = "The live response JSON payload was not an object."
        raise TypeError(msg)
    return cast("dict[str, Any]", parsed)


def response_text(response: object) -> str:
    """Return assistant text as a stripped string."""
    content = cast("Any", response).choices[0].message.content or ""
    return str(content).strip()


def usage_snapshot(response: object) -> dict[str, int] | None:
    """Return a compact usage summary when the SDK exposed token counts."""
    usage = getattr(response, "usage", None)
    if usage is None:
        return None

    return {
        "input_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
        "output_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
        "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
    }
