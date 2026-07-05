# %%
"""QwenChat workbench runtime helpers.

Why:
    Keeps local base URL selection, bearer-token env naming, and HTTP client
    construction in one place so the transport helpers and scripts share the
    same runtime settings.

When to use:
    Import from QwenChat workbench helpers or scripts that need the configured
    base URL, auth env name, or one live sync or async HTTP client.
"""

from __future__ import annotations

import os

import httpx

_DEFAULT_BASE_URL = "http://localhost:3264/api"
_DEFAULT_TIMEOUT_SECONDS = 600.0


def qwenchat_base_url() -> str:
    """Return the QwenChat base URL for this workbench suite."""
    override = os.getenv("WORKBENCH_QWENCHAT_BASE_URL", "").strip()
    return (override or _DEFAULT_BASE_URL).rstrip("/")


def api_key_env_name() -> str:
    """Return the env var that may carry the optional bearer token."""
    override = os.getenv("WORKBENCH_QWENCHAT_API_KEY_ENV", "").strip()
    return override or "QWENCHAT_API_KEY_1"


def build_sync_client() -> httpx.Client:
    """Build one sync HTTP client for QwenChat workbench calls."""
    return httpx.Client(trust_env=False, timeout=_DEFAULT_TIMEOUT_SECONDS)


def build_async_client() -> httpx.AsyncClient:
    """Build one async HTTP client for QwenChat workbench calls."""
    return httpx.AsyncClient(trust_env=False, timeout=_DEFAULT_TIMEOUT_SECONDS)


def completion_url() -> str:
    """Return the chat-completions endpoint URL."""
    return f"{qwenchat_base_url()}/chat/completions"


def upload_url() -> str:
    """Return the upload endpoint URL."""
    return f"{qwenchat_base_url()}/files/upload"
