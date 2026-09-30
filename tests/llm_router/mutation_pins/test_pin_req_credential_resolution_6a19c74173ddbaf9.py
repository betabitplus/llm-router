# mutation-pin: REQ_CREDENTIAL_RESOLUTION 6a19c74173ddbaf9
# pinned-by: claude-opus-5-5
# written-by: claude-opus-5-5, the last resort, the verdict's own model with tools
from __future__ import annotations

from dataclasses import replace

import pytest

from llm_router import (
    ApiKeyNotFoundError,
    LLMRouter,
    Model,
    Provider,
    RouterProfile,
    get_config,
    install_config,
)

pytestmark = pytest.mark.verification_kind("unit")

PROVIDER = Provider.OPENROUTER
PREFIX = f"{PROVIDER.name}_API_KEY_"
CUSTOM_ENV = f"{PREFIX}SECONDARY"


@pytest.mark.verifies("REQ_CREDENTIAL_RESOLUTION[revision==1]")
def test_auto_rotation_lists_candidates_before_missing_custom_key_surfaces(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Auto rotation resolves every candidate key while listing candidates.

    Slot 2 is discovered through its numbered variable but is configured under
    a custom environment name that is unset. Listing the auto-rotation
    candidates must resolve all slots up front, so the public request fails
    with the missing-key error for slot 2, raised by the candidate listing
    itself rather than later while the router consumes the candidates.
    """
    monkeypatch.delenv(CUSTOM_ENV, raising=False)
    monkeypatch.setenv(f"{PREFIX}1", "value-1")
    monkeypatch.setenv(f"{PREFIX}2", "value-2")
    config = get_config()
    env_names = {1: f"{PREFIX}1", 2: CUSTOM_ENV}
    spec = replace(config.catalog.providers[PROVIDER], api_key_env_vars=env_names)
    catalog = replace(
        config.catalog,
        providers={**config.catalog.providers, PROVIDER: spec},
    )
    install_config(replace(config, catalog=catalog))
    router = LLMRouter(
        RouterProfile(provider=PROVIDER, model=Model.DEEPSEEK_V3, key_id="auto"),
    )

    with pytest.raises(
        ApiKeyNotFoundError,
        match=r"OPENROUTER_API_KEY_SECONDARY.*\(ID: 2\)",
    ) as exc_info:
        router.query("Summarize the release notes.")

    error = exc_info.value
    assert (error.key_name, error.provider, error.key_id) == (
        CUSTOM_ENV,
        PROVIDER.value,
        2,
    )
    frame_names = [entry.name for entry in exc_info.traceback]
    assert "candidates" in frame_names
