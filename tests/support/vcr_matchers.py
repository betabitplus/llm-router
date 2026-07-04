"""Shared VCR matcher primitives.

Why:
    Keeps generic matcher helpers reusable across projects without mixing in
    project-specific request normalization.

When to use:
    Import from here when a test suite needs small, generic VCR matcher
    building blocks.

How:
    Compose these helpers into project-specific VCR extension modules instead
    of embedding shared matcher logic directly in one project.
"""

from __future__ import annotations

from typing import Any

from tests.support._vcr_shared import (
    compare_optional_json_bodies,
    compare_optional_multipart_single_file_content,
)

# ================================================================================
# Public API
# ================================================================================


def method_case_insensitive(r1: Any, r2: Any) -> None:
    """Match HTTP methods case-insensitively (HTTP methods are case-insensitive)."""
    method_left = str(getattr(r1, "method", "")).upper()
    method_right = str(getattr(r2, "method", "")).upper()
    if method_left != method_right:
        raise AssertionError(f"{method_left} != {method_right}")


def multipart_single_file_content(r1: Any, r2: Any) -> None:
    """Match multipart single-file uploads by extracted file content."""
    maybe_equal = compare_optional_multipart_single_file_content(r1, r2)
    if maybe_equal is None:
        msg = "requests are not both multipart single-file uploads"
        raise AssertionError(msg)
    if not maybe_equal:
        raise AssertionError("multipart single-file content differs")


def json_semantic_body(
    r1: Any,
    r2: Any,
) -> None:
    """Match JSON bodies after shared semantic normalization."""
    maybe_equal, diff_message = compare_optional_json_bodies(r1, r2)
    if maybe_equal is None:
        msg = "requests are not both JSON bodies"
        raise AssertionError(msg)
    if not maybe_equal:
        raise AssertionError(f"json body differs: {diff_message}")
