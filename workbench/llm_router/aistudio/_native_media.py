# %%
"""AI Studio native-media workbench helpers.

Why:
    The AI Studio adapter switches away from the OpenAI-compatible endpoint for
    native media inputs and talks directly to a Gemini-style streamed endpoint.
    The workbench keeps that protocol in one place so the PDF and video scripts
    stay small and readable.

When to use:
    Import from AI Studio workbench scripts that need native PDF, local-video,
    or remote-video requests against the streamed endpoint.
"""

from __future__ import annotations

import base64
import contextlib
import json
import os
import time
from pathlib import Path
from typing import Any

import httpx
from google.genai import _common, _transformers as transformers
from pydantic import BaseModel

from workbench.llm_router.aistudio._sdk_helpers import (
    api_key_env_name,
    openai_base_url,
)

_HTTP_OK = 200
_RETRYABLE_STATUS_CODES = {429, 500, 503}
_MAX_SYNC_REQUEST_ATTEMPTS = 3
_DEFAULT_RETRY_WAIT_SECONDS = 2.0


# ======================================================================================
# Native Part Builders
# ======================================================================================


def _get_video_mime_type(path_or_url: str) -> str:
    """Guess video mime type. Default to `video/mp4`."""
    if path_or_url.lower().endswith(".mov"):
        return "video/quicktime"
    return "video/mp4"


def _format_video_offset(seconds: int) -> str:
    """Format seconds into the `Xs` string required by Gemini APIs."""
    return f"{seconds}s"


def _build_video_metadata(
    *,
    fps: int | None,
    start_offset: int | None,
    end_offset: int | None,
) -> dict[str, object]:
    """Build native Gemini video metadata for one video item."""
    metadata: dict[str, object] = {}
    if fps is not None:
        metadata["fps"] = fps
    if start_offset is not None:
        metadata["startOffset"] = _format_video_offset(start_offset)
    if end_offset is not None:
        metadata["endOffset"] = _format_video_offset(end_offset)
    return metadata


def build_local_video_part(
    *,
    path: Path,
    fps: int | None,
    start_offset: int | None = None,
    end_offset: int | None = None,
) -> dict[str, object]:
    """Build one local-video Gemini part with optional metadata."""
    mime_type = _get_video_mime_type(path.name)
    video_data = base64.b64encode(path.read_bytes()).decode("utf-8")
    part: dict[str, object] = {
        "inlineData": {
            "mimeType": mime_type,
            "data": video_data,
        }
    }
    metadata = _build_video_metadata(
        fps=fps,
        start_offset=start_offset,
        end_offset=end_offset,
    )
    if metadata:
        part["videoMetadata"] = metadata
    return part


def build_local_file_part(
    *,
    path: Path,
    mime_type: str | None = None,
) -> dict[str, object]:
    """Build one local inline-data Gemini part for a non-video file."""
    resolved_mime_type = mime_type or "application/octet-stream"
    file_data = base64.b64encode(path.read_bytes()).decode("utf-8")
    return {
        "inlineData": {
            "mimeType": resolved_mime_type,
            "data": file_data,
        }
    }


def build_remote_video_part(
    *,
    url: str,
    fps: int | None,
    start_offset: int | None = None,
    end_offset: int | None = None,
) -> dict[str, object]:
    """Build one remote-video Gemini part with optional metadata."""
    mime_type = _get_video_mime_type(url)
    part: dict[str, object] = {
        "fileData": {
            "mimeType": mime_type,
            "fileUri": url,
        }
    }
    metadata = _build_video_metadata(
        fps=fps,
        start_offset=start_offset,
        end_offset=end_offset,
    )
    if metadata:
        part["videoMetadata"] = metadata
    return part


def build_text_part(text: str) -> dict[str, str]:
    """Build one plain Gemini text part."""
    return {"text": text}


# ======================================================================================
# Endpoint And Schema Helpers
# ======================================================================================


def _native_root_from_openai_base(base_url: str) -> str:
    """Derive the native AI Studio root URL from an OpenAI-style base URL."""
    normalized = base_url.rstrip("/")
    for suffix in ("/v1beta/openai", "/v1/openai", "/v1", "/openai"):
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)]
            break
    return normalized


def build_native_video_endpoint(*, model: str) -> str:
    """Build the native streamed AI Studio video endpoint for `model`."""
    api_model = model if model.startswith("models/") else f"models/{model}"
    native_root = _native_root_from_openai_base(openai_base_url())
    return f"{native_root}/v1beta/{api_model}:streamGenerateContent"


def translate_schema_to_gemini(
    schema: type[BaseModel] | dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Translate a schema to Gemini `responseSchema` format."""
    if schema is None:
        return None

    schema_obj = transformers.t_schema(None, schema)
    if schema_obj is None:
        return None
    return _common.convert_to_dict(schema_obj)


def build_native_video_payload(
    *,
    parts: list[dict[str, object]],
    response_schema: type[BaseModel] | dict[str, Any] | None,
    temperature: float | None,
) -> dict[str, object]:
    """Build one native streamed AI Studio video request payload."""
    payload: dict[str, object] = {"contents": [{"parts": parts}]}
    generation_config: dict[str, object] = {}

    if temperature is not None:
        generation_config["temperature"] = temperature
    if response_schema is not None:
        generation_config["responseMimeType"] = "application/json"
        generation_config["responseSchema"] = translate_schema_to_gemini(
            response_schema
        )
    if generation_config:
        payload["generationConfig"] = generation_config
    return payload


# ======================================================================================
# Stream Parsing Helpers
# ======================================================================================


def _collect_text_from_payloads(payloads: list[dict[str, Any]]) -> str:
    """Collect candidate text parts from parsed Gemini payload objects."""
    full_text: list[str] = []
    for data in payloads:
        candidates = data.get("candidates", [])
        if not candidates:
            continue
        content = candidates[0].get("content", {})
        parts = content.get("parts", [])
        full_text.extend(part["text"] for part in parts if "text" in part)
    return "".join(full_text)


def _parse_sse_payloads(response_lines: list[str]) -> list[dict[str, Any]]:
    """Parse SSE-style `data:` lines into Gemini payload objects."""
    payloads: list[dict[str, Any]] = []
    for line in response_lines:
        if not line or not line.startswith("data: "):
            continue
        data_str = line[6:]
        if data_str == "[DONE]":
            break
        with contextlib.suppress(json.JSONDecodeError):
            payload = json.loads(data_str)
            if isinstance(payload, dict):
                payloads.append(payload)
    return payloads


def _parse_joined_payloads(response_lines: list[str]) -> list[dict[str, Any]]:
    """Parse one joined JSON body into Gemini payload objects."""
    joined = "\n".join(response_lines).strip()
    if not joined:
        return []

    with contextlib.suppress(json.JSONDecodeError):
        payload = json.loads(joined)
        if isinstance(payload, dict):
            return [payload]
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
    return []


def parse_stream_response(response_lines: list[str]) -> str:
    """Parse streamed Gemini response lines into full text."""
    if not response_lines:
        return ""

    # Native AI Studio video responses may arrive either as SSE-style `data:`
    # lines or as one JSON array body split across physical lines.
    if any(line.startswith("data: ") for line in response_lines):
        return _collect_text_from_payloads(_parse_sse_payloads(response_lines))

    return _collect_text_from_payloads(_parse_joined_payloads(response_lines))


def parse_usage_metadata(response_lines: list[str]) -> dict[str, int]:
    """Extract usage metadata from one native streamed response."""
    joined = "\n".join(response_lines).strip()
    if not joined:
        return {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
        }

    with contextlib.suppress(json.JSONDecodeError):
        payload = json.loads(joined)
        items: list[Any]
        if isinstance(payload, dict):
            items = [payload]
        elif isinstance(payload, list):
            items = payload
        else:
            items = []

        for item in reversed(items):
            if not isinstance(item, dict):
                continue
            usage = item.get("usageMetadata")
            if not isinstance(usage, dict):
                continue
            return {
                "input_tokens": int(usage.get("promptTokenCount", 0) or 0),
                "output_tokens": int(usage.get("candidatesTokenCount", 0) or 0),
                "total_tokens": int(usage.get("totalTokenCount", 0) or 0),
            }
    return {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
    }


def parse_json_response(
    text: str,
    schema: type[BaseModel] | dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Attempt to parse JSON response text and validate if a model was provided."""
    if schema is None:
        return None

    cleaned_text = text.removeprefix("```json").removesuffix("```").strip()
    try:
        json_data = json.loads(cleaned_text)
    except (json.JSONDecodeError, ValueError):
        return None

    if isinstance(schema, type):
        return schema.model_validate(json_data).model_dump(mode="json")
    return json_data


def _retry_wait_seconds(*, error_text: str, attempt_index: int) -> float:
    """Pick a retry delay, honoring Gemini `RetryInfo` when available."""
    with contextlib.suppress(json.JSONDecodeError, TypeError, ValueError):
        payload = json.loads(error_text)
        items = payload if isinstance(payload, list) else [payload]
        for item in items:
            if not isinstance(item, dict):
                continue
            error_obj = item.get("error")
            if not isinstance(error_obj, dict):
                continue
            details = error_obj.get("details")
            if not isinstance(details, list):
                continue
            for detail in details:
                if not isinstance(detail, dict):
                    continue
                retry_delay = detail.get("retryDelay")
                if not isinstance(retry_delay, str):
                    continue
                if retry_delay.endswith("s"):
                    return max(float(retry_delay[:-1]) + 1.0, 1.0)

    return _DEFAULT_RETRY_WAIT_SECONDS * float(attempt_index + 1)


# ======================================================================================
# Sync Request Runner
# ======================================================================================


def run_sync_native_request(
    *,
    model: str,
    parts: list[dict[str, object]],
    response_schema: type[BaseModel] | dict[str, Any] | None,
    temperature: float = 0.0,
) -> dict[str, object]:
    """Run one sync native streamed AI Studio request."""
    endpoint = build_native_video_endpoint(model=model)
    payload = build_native_video_payload(
        parts=parts,
        response_schema=response_schema,
        temperature=temperature,
    )
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": os.environ[api_key_env_name()],
    }

    last_error: RuntimeError | None = None
    for attempt in range(_MAX_SYNC_REQUEST_ATTEMPTS):
        with (
            httpx.Client(trust_env=False) as client,
            client.stream(
                "POST",
                endpoint,
                json=payload,
                headers=headers,
                timeout=120.0,
            ) as response,
        ):
            if response.status_code == _HTTP_OK:
                # Read the streamed body once, then derive text, optional
                # parsed JSON, and usage evidence from the same captured lines.
                response_lines = list(response.iter_lines())
                final_text = parse_stream_response(response_lines)
                return {
                    "endpoint": endpoint,
                    "parsed": parse_json_response(final_text, response_schema),
                    "text": final_text,
                    "usage": parse_usage_metadata(response_lines),
                }

            error_text = "Could not read error body"
            with contextlib.suppress(Exception):
                error_text = response.read().decode("utf-8")
            last_error = RuntimeError(
                "The native AI Studio request failed "
                f"with {response.status_code}: {error_text}"
            )
            if response.status_code not in _RETRYABLE_STATUS_CODES or attempt == (
                _MAX_SYNC_REQUEST_ATTEMPTS - 1
            ):
                break

        time.sleep(_retry_wait_seconds(error_text=error_text, attempt_index=attempt))

    if last_error is None:  # pragma: no cover - defensive guard
        msg = "The native AI Studio request failed without an error object."
        raise RuntimeError(msg)
    raise last_error
