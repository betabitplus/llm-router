"""QwenChat workbench upload and content-assembly helpers.

Why:
    Keeps deterministic uploads and role-less user-content assembly in one
    place so the QwenChat scripts can stay focused on the seam they document.

When to use:
    Import from QwenChat workbench helpers or scripts that upload files or
    flatten text and media items into one QwenChat user-content payload.
"""

from __future__ import annotations

import asyncio
import mimetypes
import os
import time
from io import BytesIO
from pathlib import Path
from typing import Any, Literal, TypedDict, cast

import httpx
from PIL import Image

from workbench.llm_router.qwenchat._runtime import api_key_env_name, upload_url

_UPLOAD_BOUNDARY = "llm-router-qwenchat-upload"
_UPLOAD_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
_MAX_UPLOAD_ATTEMPTS = 3

type QwenMessageItem = str | Image.Image | Path


class QwenTextPart(TypedDict):
    """One text part in QwenChat mixed user content."""

    type: Literal["text"]
    text: str


class QwenImagePart(TypedDict):
    """One uploaded-image part in QwenChat mixed user content."""

    type: Literal["image"]
    image: str


class QwenFilePart(TypedDict):
    """One uploaded-file part in QwenChat mixed user content."""

    type: Literal["file"]
    file: str


type QwenContentPart = QwenTextPart | QwenImagePart | QwenFilePart
type QwenUserContent = str | list[QwenContentPart]


# ======================================================================================
# Upload Headers And Validation
# ======================================================================================


def _auth_headers() -> dict[str, str]:
    """Build optional auth headers for the local proxy."""
    api_key = os.getenv(api_key_env_name(), "").strip()
    if not api_key:
        return {}
    return {"Authorization": f"Bearer {api_key}"}


def _upload_headers(content_type: str) -> dict[str, str]:
    """Build headers for `/files/upload` requests."""
    return {
        "Content-Type": content_type,
        "Accept": "application/json",
        **_auth_headers(),
    }


def encode_multipart_single_file(
    *,
    filename: str,
    content_type: str,
    content: bytes,
) -> tuple[bytes, str]:
    """Encode one deterministic multipart/form-data upload body."""
    boundary_bytes = _UPLOAD_BOUNDARY.encode("utf-8")
    crlf = b"\r\n"
    body = crlf.join(
        [
            b"--" + boundary_bytes,
            (
                f'Content-Disposition: form-data; name="file"; filename="{filename}"'
            ).encode(),
            f"Content-Type: {content_type}".encode(),
            b"",
            content,
            b"--" + boundary_bytes + b"--",
            b"",
        ]
    )
    return body, f"multipart/form-data; boundary={_UPLOAD_BOUNDARY}"


def _extract_upload_url(response: dict[str, Any]) -> str:
    """Extract the uploaded file URL from one QwenChat upload response."""
    file_obj = response.get("file")
    if not isinstance(file_obj, dict):
        msg = "The live upload response did not include a `file` object."
        raise TypeError(msg)

    file_url = file_obj.get("url")
    if not isinstance(file_url, str) or not file_url:
        msg = "The live upload response did not include `file.url`."
        raise TypeError(msg)
    return file_url


def _is_retryable_upload_response(response: httpx.Response) -> bool:
    """Return whether one upload response should be retried."""
    return response.status_code in _UPLOAD_RETRYABLE_STATUS_CODES


# ======================================================================================
# Sync Uploads
# ======================================================================================


def upload_bytes_sync(
    *,
    client: httpx.Client,
    filename: str,
    content_type: str,
    content: bytes,
) -> str:
    """Upload one file body to QwenChat and return the uploaded URL."""
    body, multipart_type = encode_multipart_single_file(
        filename=filename,
        content_type=content_type,
        content=content,
    )
    last_error: RuntimeError | None = None
    for attempt in range(_MAX_UPLOAD_ATTEMPTS):
        try:
            response = client.post(
                upload_url(),
                headers=_upload_headers(multipart_type),
                content=body,
            )
        except httpx.RequestError as exc:
            last_error = RuntimeError(
                f"The live QwenChat upload request failed before a response: {exc}"
            )
            if attempt == (_MAX_UPLOAD_ATTEMPTS - 1):
                break
            time.sleep(float(attempt + 1))
            continue

        if response.is_success:
            return _extract_upload_url(cast("dict[str, Any]", response.json()))

        last_error = RuntimeError(
            f"The live QwenChat upload request failed with "
            f"{response.status_code}: {response.text}"
        )
        if not _is_retryable_upload_response(response) or attempt == (
            _MAX_UPLOAD_ATTEMPTS - 1
        ):
            break
        time.sleep(float(attempt + 1))

    if last_error is None:  # pragma: no cover - defensive guard
        msg = "The live QwenChat upload request failed without an error object."
        raise RuntimeError(msg)
    raise last_error


# ======================================================================================
# Async Uploads
# ======================================================================================


async def upload_bytes_async(
    *,
    client: httpx.AsyncClient,
    filename: str,
    content_type: str,
    content: bytes,
) -> str:
    """Upload one file body to QwenChat and return the uploaded URL."""
    body, multipart_type = encode_multipart_single_file(
        filename=filename,
        content_type=content_type,
        content=content,
    )
    last_error: RuntimeError | None = None
    for attempt in range(_MAX_UPLOAD_ATTEMPTS):
        try:
            response = await client.post(
                upload_url(),
                headers=_upload_headers(multipart_type),
                content=body,
            )
        except httpx.RequestError as exc:
            last_error = RuntimeError(
                f"The live QwenChat upload request failed before a response: {exc}"
            )
            if attempt == (_MAX_UPLOAD_ATTEMPTS - 1):
                break
            await asyncio.sleep(float(attempt + 1))
            continue

        if response.is_success:
            return _extract_upload_url(cast("dict[str, Any]", response.json()))

        last_error = RuntimeError(
            f"The live QwenChat upload request failed with "
            f"{response.status_code}: {response.text}"
        )
        if not _is_retryable_upload_response(response) or attempt == (
            _MAX_UPLOAD_ATTEMPTS - 1
        ):
            break
        await asyncio.sleep(float(attempt + 1))

    if last_error is None:  # pragma: no cover - defensive guard
        msg = "The live QwenChat upload request failed without an error object."
        raise RuntimeError(msg)
    raise last_error


# ======================================================================================
# Upload Conveniences
# ======================================================================================


def _image_to_png_bytes(image: Image.Image) -> bytes:
    """Encode one PIL image to PNG bytes for upload."""
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def upload_image_sync(*, client: httpx.Client, image: Image.Image) -> str:
    """Upload one PIL image to QwenChat and return the uploaded URL."""
    return upload_bytes_sync(
        client=client,
        filename="image.png",
        content_type="image/png",
        content=_image_to_png_bytes(image),
    )


async def upload_image_async(
    *,
    client: httpx.AsyncClient,
    image: Image.Image,
) -> str:
    """Upload one PIL image to QwenChat and return the uploaded URL."""
    return await upload_bytes_async(
        client=client,
        filename="image.png",
        content_type="image/png",
        content=_image_to_png_bytes(image),
    )


def _path_upload_spec(path: Path) -> tuple[str, str, bytes]:
    """Build upload metadata for one local file path."""
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return path.name, mime_type, path.read_bytes()


def _is_image_path(path: Path) -> bool:
    """Return whether one local path should become a QwenChat image part."""
    mime_type = mimetypes.guess_type(path.name)[0] or ""
    return mime_type.startswith("image/")


def upload_path_sync(*, client: httpx.Client, path: Path) -> str:
    """Upload one local file path to QwenChat and return the uploaded URL."""
    filename, content_type, content = _path_upload_spec(path)
    return upload_bytes_sync(
        client=client,
        filename=filename,
        content_type=content_type,
        content=content,
    )


async def upload_path_async(
    *,
    client: httpx.AsyncClient,
    path: Path,
) -> str:
    """Upload one local file path to QwenChat and return the uploaded URL."""
    filename, content_type, content = await asyncio.to_thread(_path_upload_spec, path)
    return await upload_bytes_async(
        client=client,
        filename=filename,
        content_type=content_type,
        content=content,
    )


# ======================================================================================
# User-Content Assembly
# ======================================================================================


def _text_part(text: str) -> QwenTextPart:
    """Build one QwenChat text part."""
    return {
        "type": "text",
        "text": text,
    }


def _image_part(image_url: str) -> QwenImagePart:
    """Build one QwenChat image part."""
    return {
        "type": "image",
        "image": image_url,
    }


def _file_part(file_url: str) -> QwenFilePart:
    """Build one QwenChat file part."""
    return {
        "type": "file",
        "file": file_url,
    }


def build_user_content_sync(
    *,
    client: httpx.Client,
    items: list[QwenMessageItem],
) -> QwenUserContent:
    """Flatten role-less workbench items into one QwenChat user content value."""
    parts: list[QwenContentPart] = []
    buffer: list[str] = []

    def flush_text() -> None:
        """Flush buffered text chunks into one QwenChat text part."""
        if not buffer:
            return
        parts.append(_text_part("\n\n".join(buffer)))
        buffer.clear()

    for item in items:
        if isinstance(item, str):
            buffer.append(item)
            continue

        # Keep consecutive text together, but turn binary items into uploaded
        # image or file parts as soon as they appear.
        flush_text()
        if isinstance(item, Image.Image):
            parts.append(_image_part(upload_image_sync(client=client, image=item)))
            continue
        if _is_image_path(item):
            parts.append(_image_part(upload_path_sync(client=client, path=item)))
            continue
        parts.append(_file_part(upload_path_sync(client=client, path=item)))

    flush_text()
    if len(parts) == 1 and parts[0]["type"] == "text":
        return parts[0]["text"]
    return parts


async def build_user_content_async(
    *,
    client: httpx.AsyncClient,
    items: list[QwenMessageItem],
) -> QwenUserContent:
    """Flatten role-less workbench items into one QwenChat user content value."""
    parts: list[QwenContentPart] = []
    buffer: list[str] = []

    def flush_text() -> None:
        """Flush buffered text chunks into one QwenChat text part."""
        if not buffer:
            return
        parts.append(_text_part("\n\n".join(buffer)))
        buffer.clear()

    for item in items:
        if isinstance(item, str):
            buffer.append(item)
            continue

        # Keep consecutive text together, but turn binary items into uploaded
        # image or file parts as soon as they appear.
        flush_text()
        if isinstance(item, Image.Image):
            image_url = await upload_image_async(client=client, image=item)
            parts.append(_image_part(image_url))
            continue
        if _is_image_path(item):
            image_url = await upload_path_async(client=client, path=item)
            parts.append(_image_part(image_url))
            continue
        file_url = await upload_path_async(client=client, path=item)
        parts.append(_file_part(file_url))

    flush_text()
    if len(parts) == 1 and parts[0]["type"] == "text":
        return parts[0]["text"]
    return parts
