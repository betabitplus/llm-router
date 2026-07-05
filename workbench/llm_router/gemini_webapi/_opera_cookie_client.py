# %%
"""Internal Gemini WebAPI Opera-cookie client helpers.

Why:
    Centralizes the real local cookie bootstrap used by the Gemini WebAPI
    workbench scripts so each scenario can stay focused on one SDK seam.

When to use:
    Import from Gemini WebAPI workbench scripts that need Opera cookie access,
    runtime preflight checks, or a ready-to-init live client.
"""

from __future__ import annotations

import contextlib
import os
import tempfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gemini_webapi import GeminiClient

_DEFAULT_OPERA_COOKIE_FILE = (
    Path.home() / "Library/Application Support/com.operasoftware.Opera/Default/Cookies"
)
_COOKIE_DOMAIN = "google.com"
_COOKIE_CACHE_DIR = (
    Path(tempfile.gettempdir()) / "llm_router_gemini_webapi_cookie_cache"
)


# ======================================================================================
# Local Runtime Paths
# ======================================================================================


def opera_cookie_file_path() -> Path:
    """Return the configured Opera cookie database path."""
    override = os.getenv("WORKBENCH_OPERA_COOKIE_FILE") or os.getenv(
        "LLM_ROUTER_OPERA_COOKIE_FILE"
    )
    return (Path(override) if override else _DEFAULT_OPERA_COOKIE_FILE).expanduser()


def cookie_cache_dir() -> Path:
    """Return the cache directory used by `gemini_webapi` cookie state."""
    return _COOKIE_CACHE_DIR


def _ensure_cookie_cache_dir() -> Path:
    """Ensure the SDK cookie-cache directory exists and is configured."""
    configured = os.getenv("GEMINI_COOKIE_PATH")
    if configured:
        return Path(configured).expanduser()

    _COOKIE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    os.environ["GEMINI_COOKIE_PATH"] = str(_COOKIE_CACHE_DIR)
    return _COOKIE_CACHE_DIR


# ======================================================================================
# Cookie Extraction
# ======================================================================================


def cookie_lookup() -> dict[str, str]:
    """Return the decrypted google.com cookie lookup used by Gemini WebAPI."""
    import browser_cookie3

    cookie_file = opera_cookie_file_path()
    with tempfile.TemporaryDirectory(prefix="llm_router_opera_cookies_") as td:
        temp_cookie_file = Path(td) / "Cookies"
        temp_cookie_file.write_bytes(cookie_file.read_bytes())
        jar = browser_cookie3.opera(
            cookie_file=str(temp_cookie_file),
            domain_name=_COOKIE_DOMAIN,
        )
        return {cookie.name: cookie.value for cookie in jar}


# ======================================================================================
# Runtime Preflight
# ======================================================================================


def runtime_status() -> dict[str, object]:
    """Return a compact runtime status summary for the local cookie setup."""
    cookie_file = opera_cookie_file_path()
    if not cookie_file.exists():
        return {
            "ready": False,
            "reason": f"Opera Cookies DB not found: {cookie_file}",
        }

    try:
        lookup = cookie_lookup()
    except Exception as exc:  # pragma: no cover - environment-dependent
        return {
            "ready": False,
            "reason": f"Opera cookie decryption not available: {exc}",
        }

    has_1psid = "__Secure-1PSID" in lookup
    if not has_1psid:
        return {
            "ready": False,
            "reason": "Missing __Secure-1PSID in Opera cookies for google.com",
        }

    return {
        "ready": True,
        "cookie_file": str(cookie_file),
        "cookie_cache_dir": str(_ensure_cookie_cache_dir()),
        "has_secure_1psid": True,
        "has_secure_1psidts": "__Secure-1PSIDTS" in lookup,
        "has_nid": "NID" in lookup,
    }


# ======================================================================================
# Client Lifecycle Helpers
# ======================================================================================


def build_client() -> GeminiClient:
    """Build one live Gemini WebAPI client from local Opera cookies."""
    from gemini_webapi import GeminiClient

    _ensure_cookie_cache_dir()
    lookup = cookie_lookup()
    client = GeminiClient(
        lookup["__Secure-1PSID"],
        lookup.get("__Secure-1PSIDTS"),
        proxy=None,
    )
    nid = lookup.get("NID")
    if nid:
        with contextlib.suppress(Exception):
            client.cookies.set("NID", nid, domain=".google.com")
    return client


async def init_client(
    client: GeminiClient,
    *,
    init_timeout_seconds: float = 30.0,
) -> GeminiClient:
    """Initialize one live Gemini WebAPI client with provider-aligned settings."""
    await client.init(
        timeout=float(init_timeout_seconds),
        auto_close=False,
        close_delay=300,
        auto_refresh=True,
        verbose=False,
    )
    return client


@asynccontextmanager
async def managed_client(
    *,
    init_timeout_seconds: float = 30.0,
) -> AsyncIterator[GeminiClient]:
    """Yield one initialized live Gemini WebAPI client and always close it."""
    client = build_client()
    await init_client(client, init_timeout_seconds=init_timeout_seconds)
    try:
        yield client
    finally:
        await client.close()
