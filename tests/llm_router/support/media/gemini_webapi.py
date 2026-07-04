"""llm_router-specific Gemini WebAPI runtime checks.

Why:
    Gemini WebAPI scenarios depend on local browser cookies and environment
    state that other llm_router tests do not need.

When to use:
    Import from here before running Gemini WebAPI tests or manual demos that
    require Opera cookie access.

How:
    Use `require_runtime()` in pytest flows and `can_run_demo()` in manual
    entry points that should report missing local prerequisites cleanly.

Examples:
    require_runtime()
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

_DEFAULT_OPERA_COOKIE_FILE = (
    Path.home() / "Library/Application Support/com.operasoftware.Opera/Default/Cookies"
)


def opera_cookie_file_path() -> Path:
    """Return the configured Opera cookie database path."""
    override = os.getenv("LLM_ROUTER_OPERA_COOKIE_FILE")
    return (Path(override) if override else _DEFAULT_OPERA_COOKIE_FILE).expanduser()


def unavailable_reason() -> str | None:
    """Return a human-readable reason if Opera Gemini cookies are unavailable."""
    cookie_file = opera_cookie_file_path()
    if not cookie_file.exists():
        return f"Opera Cookies DB not found: {cookie_file}"

    try:
        import browser_cookie3
    except Exception as exc:  # pragma: no cover
        return f"browser-cookie3 not available: {exc}"

    try:
        jar = browser_cookie3.opera(
            cookie_file=str(cookie_file),
            domain_name="google.com",
        )
    except Exception as exc:
        return f"Opera cookie decryption not available in this environment: {exc}"

    if "__Secure-1PSID" not in {c.name for c in jar}:
        return "Missing __Secure-1PSID in Opera cookies for google.com"

    return None


def require_runtime() -> None:
    """Skip the test if Gemini WebAPI runtime prerequisites are unavailable."""
    reason = unavailable_reason()
    if reason is not None:
        pytest.skip(reason)  # type: ignore[too-many-positional-arguments]


def can_run_demo() -> tuple[bool, str | None]:
    """Return whether the manual demo can run, plus the blocking reason if any."""
    reason = unavailable_reason()
    return reason is None, reason
