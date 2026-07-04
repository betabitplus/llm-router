"""Private llm_router VCR body-matching helpers.

Why:
    Keeps llm_router request-body normalization and provider-specific matching
    logic out of the shared `tests.support` layer.

When to use:
    Import from here only through `tests.llm_router.support.vcr_extensions`
    unless a test needs to exercise the matcher directly.

How:
    `body_llmrouter(...)` orchestrates specialized matching before falling back
    to VCR's built-in body matcher.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import parse_qs, urlparse

from vcr import matchers as vcr_matchers

from tests.support._vcr_shared import (
    compare_optional_json_bodies,
    compare_optional_multipart_single_file_content,
    get_header_value,
    normalize_json_body,
    to_bytes,
)

_QWEN_COMPLETION_HOST = "localhost"
_QWEN_COMPLETION_PATH = "/api/chat/completions"
_QWEN_COMPLETION_PORT = 3264
_QWEN_UPLOAD_HOST = "qwen-webui-prod.oss-accelerate.aliyuncs.com"
_GEMINI_FORM_HOST = "gemini.google.com"
_GEMINI_FORM_CONTENT_TYPE = "application/x-www-form-urlencoded"


# ================================================================================
# Public API
# ================================================================================


def body_llmrouter(r1: Any, r2: Any) -> None:
    """Match llm_router request bodies with provider-aware normalization."""
    if _handled_optional_match(
        _multipart_single_file_content_equal(r1, r2),
        "multipart single-file content differs",
    ):
        return

    if _handled_optional_match(
        _gemini_form_body_equal(r1, r2),
        "gemini form body differs",
    ):
        return

    if _handled_optional_match(
        _qwen_completion_body_equal(r1, r2),
        "qwen completion body differs",
    ):
        return

    maybe_equal, diff_message = _json_body_equal(r1, r2)
    if maybe_equal is not None:
        if not maybe_equal:
            raise AssertionError(f"json body differs: {diff_message}")
        return

    vcr_matchers.body(r1, r2)


# ================================================================================
# Match Flow Helpers
# ================================================================================


def _handled_optional_match(maybe_equal: bool | None, mismatch_message: str) -> bool:
    """Raise on mismatch and report whether one specialized matcher handled the body."""
    if maybe_equal is None:
        return False
    if not maybe_equal:
        raise AssertionError(mismatch_message)
    return True


# ================================================================================
# Specialized Body Matchers
# ================================================================================


def _multipart_single_file_content_equal(r1: Any, r2: Any) -> bool | None:
    return compare_optional_multipart_single_file_content(r1, r2)


def _gemini_form_body_equal(r1: Any, r2: Any) -> bool | None:
    if not _is_gemini_form_request(r1) or not _is_gemini_form_request(r2):
        return None

    params_left = _normalized_gemini_form_params(to_bytes(getattr(r1, "body", None)))
    params_right = _normalized_gemini_form_params(to_bytes(getattr(r2, "body", None)))
    if params_left is None or params_right is None:
        return None
    return params_left == params_right


def _qwen_completion_body_equal(r1: Any, r2: Any) -> bool | None:
    if not _is_qwen_completion_request(r1) or not _is_qwen_completion_request(r2):
        return None

    payload_left = _normalized_qwen_completion_payload(
        to_bytes(getattr(r1, "body", None))
    )
    payload_right = _normalized_qwen_completion_payload(
        to_bytes(getattr(r2, "body", None))
    )
    if payload_left is None or payload_right is None:
        return None
    return payload_left == payload_right


def _json_body_equal(r1: Any, r2: Any) -> tuple[bool | None, str | None]:
    return compare_optional_json_bodies(r1, r2)


# ================================================================================
# Provider-Specific Normalization
# ================================================================================


def _is_qwen_completion_request(request: Any) -> bool:
    uri = str(getattr(request, "uri", ""))
    parsed = urlparse(uri)
    if parsed.hostname != _QWEN_COMPLETION_HOST:
        return False
    if parsed.port != _QWEN_COMPLETION_PORT:
        return False
    return parsed.path == _QWEN_COMPLETION_PATH


def _normalized_qwen_completion_payload(body: bytes) -> dict[str, Any] | None:
    return normalize_json_body(body, string_normalizer=_normalize_qwen_upload_url)


def _normalize_qwen_upload_url(value: str) -> str:
    if _QWEN_UPLOAD_HOST not in value:
        return value
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"}:
        return value
    return (
        f"{parsed.scheme}://{parsed.netloc}/<qwen-upload>"
        f"?type={_qwen_upload_kind(parsed.path)}"
    )


def _qwen_upload_kind(path: str) -> str:
    lowered = path.lower()
    if lowered.endswith(".png"):
        return "image"
    if lowered.endswith(".pdf"):
        return "file"
    return "asset"


def _is_gemini_form_request(request: Any) -> bool:
    uri = str(getattr(request, "uri", ""))
    parsed = urlparse(uri)
    if parsed.hostname != _GEMINI_FORM_HOST:
        return False

    content_type = get_header_value(request, "content-type").lower()
    return _GEMINI_FORM_CONTENT_TYPE in content_type


def _normalized_gemini_form_params(body: bytes) -> dict[str, list[str]] | None:
    if not body:
        return None

    text = body.decode("utf-8", errors="strict")
    params = parse_qs(text, keep_blank_values=True)
    params.pop("at", None)
    return {
        key: sorted(_normalize_gemini_form_value(key, value) for value in values)
        for key, values in sorted(params.items())
    }


def _normalize_gemini_form_value(key: str, value: str) -> str:
    if key != "f.req":
        return value
    value = re.sub(
        r"/contrib_service/ttl_1d/[A-Za-z0-9]+",
        "/contrib_service/ttl_1d/<upload>",
        value,
    )
    return re.sub(r"image_[0-9a-f]+\.png", "image_<temp>.png", value)
