"""QwenChat workbench chat-completion helpers.

Why:
    Keeps payload assembly, completion requests, and response inspection in one
    place so the QwenChat scripts can read like scenario walkthroughs.

When to use:
    Import from QwenChat workbench helpers or scripts that send direct
    `/chat/completions` requests or inspect the returned text and usage fields.
"""

from __future__ import annotations

import os
from typing import Literal, TypedDict, cast

import httpx

from workbench.llm_router.qwenchat._runtime import (
    api_key_env_name,
    completion_url,
)
from workbench.llm_router.qwenchat._uploads import QwenUserContent


class QwenUserMessage(TypedDict):
    """One user-role message in the direct QwenChat payload."""

    role: Literal["user"]
    content: QwenUserContent


class QwenCompletionPayload(TypedDict, total=False):
    """One direct QwenChat completion payload."""

    model: str
    messages: list[QwenUserMessage]
    stream: bool
    temperature: float
    seed: int


class QwenResponseMessage(TypedDict, total=False):
    """One assistant message inside the QwenChat response."""

    content: str


class QwenResponseChoice(TypedDict, total=False):
    """One choice object inside the QwenChat response."""

    message: QwenResponseMessage


class QwenRawUsage(TypedDict, total=False):
    """Raw usage fields exposed by QwenChat responses."""

    prompt_tokens: int
    input_tokens: int
    completion_tokens: int
    output_tokens: int
    total_tokens: int


class QwenCompletionResponse(TypedDict, total=False):
    """One direct QwenChat completion response body."""

    choices: list[QwenResponseChoice]
    usage: QwenRawUsage


class QwenUsageSummary(TypedDict):
    """Normalized token-count evidence for workbench output."""

    input_tokens: int
    output_tokens: int
    total_tokens: int


# ======================================================================================
# Request Helpers
# ======================================================================================


def _auth_headers() -> dict[str, str]:
    """Build optional auth headers for the local proxy."""
    api_key = os.getenv(api_key_env_name(), "").strip()
    if not api_key:
        return {}
    return {"Authorization": f"Bearer {api_key}"}


def _completion_headers() -> dict[str, str]:
    """Build headers for `/chat/completions` requests."""
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        **_auth_headers(),
    }


def _raise_for_status(response: httpx.Response, *, context: str) -> None:
    """Raise a helpful error when one live QwenChat request failed."""
    if response.is_success:
        return
    msg = (
        f"The live QwenChat {context} request failed with "
        f"{response.status_code}: {response.text}"
    )
    raise RuntimeError(msg)


def build_payload(
    *,
    model: str,
    user_content: QwenUserContent,
    temperature: float | None,
    seed: int | None,
) -> QwenCompletionPayload:
    """Build one QwenChat chat-completions payload."""
    payload: QwenCompletionPayload = {
        "model": model,
        "messages": [{"role": "user", "content": user_content}],
        "stream": False,
    }
    if temperature is not None:
        payload["temperature"] = float(temperature)
    if seed is not None:
        payload["seed"] = int(seed)
    return payload


def post_completion_sync(
    *,
    client: httpx.Client,
    payload: QwenCompletionPayload,
) -> QwenCompletionResponse:
    """POST one sync completion request and return the JSON body."""
    response = client.post(
        completion_url(),
        headers=_completion_headers(),
        json=payload,
    )
    _raise_for_status(response, context="completion")
    return cast("QwenCompletionResponse", response.json())


async def post_completion_async(
    *,
    client: httpx.AsyncClient,
    payload: QwenCompletionPayload,
) -> QwenCompletionResponse:
    """POST one async completion request and return the JSON body."""
    response = await client.post(
        completion_url(),
        headers=_completion_headers(),
        json=payload,
    )
    _raise_for_status(response, context="completion")
    return cast("QwenCompletionResponse", response.json())


# ======================================================================================
# Response Inspection
# ======================================================================================


def response_text(response: QwenCompletionResponse) -> str:
    """Extract assistant text from one QwenChat completion response."""
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        msg = "The live QwenChat response did not include `choices`."
        raise TypeError(msg)

    message = choices[0].get("message")
    if not isinstance(message, dict):
        msg = "The live QwenChat response did not include `choices[0].message`."
        raise TypeError(msg)

    content = message.get("content")
    if not isinstance(content, str):
        msg = "The live QwenChat response did not include text content."
        raise TypeError(msg)
    return content.strip()


def usage_snapshot(response: QwenCompletionResponse) -> QwenUsageSummary | None:
    """Normalize QwenChat usage into prompt/completion/total token counts."""
    usage = response.get("usage")
    if not isinstance(usage, dict):
        return None

    input_tokens = int(usage.get("prompt_tokens", usage.get("input_tokens", 0)) or 0)
    output_tokens = int(
        usage.get("completion_tokens", usage.get("output_tokens", 0)) or 0
    )
    total_tokens = int(usage.get("total_tokens", input_tokens + output_tokens) or 0)
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
    }
