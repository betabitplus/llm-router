"""Shared setup for BDD scenarios that need Gemini WebAPI replay preparation."""

from __future__ import annotations

import pytest

from llm_router._internal.providers import gemini_webapi as gemini_webapi_provider


def prepare_gemini_webapi_runtime(
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> None:
    """Use fake cookie metadata for replay and real browser cookies for live runs."""
    if request.config.getoption("--disable-recording", default=False):
        from tests.llm_router.support.media.gemini_webapi import require_runtime

        require_runtime()
        return
    monkeypatch.setattr(
        gemini_webapi_provider,
        "cookie_lookup",
        lambda: {"__Secure-1PSID": "replay", "__Secure-1PSIDTS": "replay"},
    )
