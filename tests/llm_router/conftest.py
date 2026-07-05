"""LLMRouter pytest configuration for product-specific tests.

Why:
    Keeps package-specific runtime hooks, VCR setup, provider stubs, and cache
    isolation close to the tests that need them while leaving root pytest setup
    reusable across future repositories.

When to use:
    Put fixtures here when they import `llm_router`, depend on provider
    behavior, or configure LLMRouter-specific replay behavior.
"""

from __future__ import annotations

# =============================================================================
# Beartype Import Hook (must be before any llm_router imports)
# =============================================================================
# This enables runtime type checking for all llm_router module functions.
# Catches type errors that static analyzers (pyright/mypy) might miss.
try:
    from beartype.claw import beartype_this_package
except ModuleNotFoundError:  # pragma: no cover
    beartype_this_package = None
else:
    beartype_this_package()

import os
import tempfile
import types
from contextlib import suppress
from types import SimpleNamespace
from typing import Any

import pytest

from tests.llm_router.support.runtime import clear_test_caches
from tests.llm_router.support.vcr_extensions import (
    FILTER_HEADERS,
    MATCH_ON,
)
from py_lib_tooling import multipart_signature_prefix
from py_lib_tooling import configure_pytest_process

configure_pytest_process()


def _install_fast_fake_browser_cookie3() -> None:
    """Avoid expensive real browser-cookie decryption during tests.

    Gemini WebAPI tests are hermetic (VCR + local stubs) and should not depend
    on real Opera cookies existing or being decryptable. The upstream
    `browser_cookie3` import path can spawn subprocesses on macOS to access the
    keychain; we replace it with a tiny deterministic stub.
    """

    if os.getenv("LLM_ROUTER_USE_REAL_BROWSER_COOKIES") == "1":
        return

    # Ensure the cookie DB path check passes everywhere.
    if "LLM_ROUTER_OPERA_COOKIE_FILE" not in os.environ:
        fd, path = tempfile.mkstemp(
            prefix="llm_router_opera_cookie_",
            suffix=".sqlite3",
        )
        os.close(fd)
        os.environ["LLM_ROUTER_OPERA_COOKIE_FILE"] = path

    fake = types.ModuleType("browser_cookie3")

    def opera(*, cookie_file: str, domain_name: str):
        _ = cookie_file
        _ = domain_name
        return [
            SimpleNamespace(name="__Secure-1PSID", value="local-1psid"),
            SimpleNamespace(name="__Secure-1PSIDTS", value="local-1psidts"),
            SimpleNamespace(name="NID", value="local-nid"),
        ]

    fake.opera = opera  # type: ignore[attr-defined]
    import sys

    sys.modules["browser_cookie3"] = fake


_install_fast_fake_browser_cookie3()


# =============================================================================
# VCR Configuration
# =============================================================================


def pytest_recording_configure(config: pytest.Config, vcr: Any) -> None:  # noqa: ARG001
    """Configure pytest-recording's VCR instance for LLMRouter tests."""
    from tests.llm_router.support.vcr_extensions import register_vcr_extensions

    register_vcr_extensions(vcr)


@pytest.fixture(scope="module")
def vcr_config() -> dict[str, Any]:
    """Configure VCR for LLMRouter HTTP recording."""

    return {
        "filter_headers": FILTER_HEADERS,
        # Match on body to ensure different requests get different cassettes
        "match_on": MATCH_ON,
        # Important for polling/streaming providers (e.g. Gemini WebAPI): a single
        # logical request may retry/poll multiple times with an identical body.
        # We want VCR to consume the next recorded interaction rather than
        # replaying the first match repeatedly.
        "allow_playback_repeats": False,
        # Decode gzip/deflate/br during recording for stable replay cassettes.
        "decode_compressed_response": True,
        # Safety: avoid persisting browser/session cookies in new recordings.
        "before_record_request": _vcr_scrub_request,
        "before_record_response": _vcr_scrub_response,
    }


def _vcr_scrub_request(request: Any) -> Any:
    import json

    headers = getattr(request, "headers", None)
    if isinstance(headers, dict):
        headers.pop("Cookie", None)
        headers.pop("cookie", None)

    # Keep recording artifacts small: multipart uploads and JSON payloads with
    # embedded base64 media can produce multi-megabyte cassettes. Replace the
    # recorded request body with a stable semantic signature so replay still
    # matches while keeping cassettes under the repository size guard.
    try:
        from py_lib_tooling import (
            extract_boundary,
            extract_single_part_content,
            get_header_value,
            is_png,
            normalize_inline_media_bytes,
            normalize_json_body,
            to_bytes,
        )

        content_type = get_header_value(request, "content-type")
        boundary = extract_boundary(content_type)
        if boundary:
            raw_body = to_bytes(getattr(request, "body", None))
            content = extract_single_part_content(raw_body, boundary)
            if content is not None:
                mime_type = (
                    "image/png" if is_png(content) else "application/octet-stream"
                )
                signature = normalize_inline_media_bytes(
                    mime_type=mime_type,
                    data=content,
                )
                request.body = multipart_signature_prefix().decode(
                    "ascii"
                ) + json.dumps(signature, sort_keys=True, separators=(",", ":"))
                return request

        if "application/json" in content_type.lower():
            raw_body = to_bytes(getattr(request, "body", None))
            if len(raw_body) > 200_000:
                normalized = normalize_json_body(raw_body)
                if normalized is not None:
                    request.body = json.dumps(
                        normalized,
                        sort_keys=True,
                        separators=(",", ":"),
                    )
    except Exception:
        # Defensive: never fail the test suite just because VCR scrubbing
        # couldn't parse one payload.
        return request

    return request


def _vcr_scrub_response(response: Any) -> Any:
    if isinstance(response, dict):
        headers = response.get("headers")
        if isinstance(headers, dict):
            headers.pop("Set-Cookie", None)
            headers.pop("set-cookie", None)
    return response


# =============================================================================
# Test Isolation
# =============================================================================


@pytest.fixture(scope="session", autouse=True)
def provide_dummy_api_keys_for_tests(
    pytestconfig: pytest.Config,
) -> None:
    """Ensure API keys exist for VCR-replayed tests without real secrets."""
    if _pytest_record_mode(pytestconfig) not in {None, "none"}:
        return

    os.environ.setdefault("AISTUDIO_API_KEY_1", "DUMMY_FOR_VCR_REPLAY")
    os.environ.setdefault("GOOGLE_API_KEY_1", "DUMMY_FOR_VCR_REPLAY")
    os.environ.setdefault("MISTRAL_API_KEY_1", "DUMMY_FOR_VCR_REPLAY")
    os.environ.setdefault("NVIDIA_API_KEY_1", "DUMMY_FOR_VCR_REPLAY")
    os.environ.setdefault("OPENROUTER_API_KEY_1", "DUMMY_FOR_VCR_REPLAY")
    os.environ.setdefault("QWENCHAT_API_KEY_1", "DUMMY_FOR_VCR_REPLAY")


def _pytest_record_mode(pytestconfig: pytest.Config) -> str | None:
    """Return pytest-recording's effective record mode, if available."""
    for option in ("record_mode", "--record-mode"):
        with suppress(Exception):
            value = pytestconfig.getoption(option)
            if isinstance(value, str):
                return value
    return None


@pytest.fixture(autouse=True)
def clear_cached_client_singletons() -> None:
    """Reset singleton provider clients between tests for cassette isolation."""
    _clear_cached_client_factories()
    yield
    _clear_cached_client_factories()


@pytest.fixture(autouse=True)
def reset_installed_llm_router_config() -> None:
    """Restore the installed runtime config after each test."""
    from llm_router import get_config, install_config

    original = get_config()
    install_config(original)
    yield
    install_config(original)


def _clear_cached_client_factories() -> None:
    """Clear cached singleton client factories used by router instances."""
    clear_test_caches()
