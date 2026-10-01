# mutation-pin: REQ_CREDENTIAL_RESOLUTION b424da4f88707d25
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
CUSTOM_SLOT = 3
CUSTOM_ENV_NAME = "OPENROUTER_BACKUP_CREDENTIAL"


class GatedSlot(int):
    """Pinned numeric key slot that also passes the router's auto gate.

    The router only lists key candidates when the requested key id equals
    ``"auto"``; candidate listing itself then treats any value that differs
    from ``"auto"`` as a fixed key id.  This slot equals ``"auto"`` for the
    gate but differs from it for ``!=``, so a public request reaches the
    fixed-key branch of candidate listing with a concrete numeric slot.
    """

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return other == "auto"
        return int(self) == other

    def __ne__(self, other: object) -> bool:
        return int(self) != other

    __hash__ = int.__hash__


def _install_custom_env_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(CUSTOM_ENV_NAME, raising=False)
    config = get_config()
    spec = config.catalog.providers[PROVIDER]
    env_names = {**spec.api_key_env_vars, CUSTOM_SLOT: CUSTOM_ENV_NAME}
    catalog = replace(
        config.catalog,
        providers={
            **config.catalog.providers,
            PROVIDER: replace(spec, api_key_env_vars=env_names),
        },
    )
    install_config(replace(config, catalog=catalog))


@pytest.mark.verifies("REQ_CREDENTIAL_RESOLUTION[revision==1]")
def test_fixed_candidate_resolves_custom_env_name_and_reports_missing_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A fixed slot mapped to a custom env name is resolved through that name.

    With the custom variable unset, candidate listing for the fixed slot must
    resolve the slot itself and surface the public missing-key error naming
    the custom environment variable, the provider and the slot.
    """
    _install_custom_env_name(monkeypatch)
    router = LLMRouter(
        RouterProfile(
            model=Model.DEEPSEEK_V3,
            provider=PROVIDER,
            key_id=GatedSlot(CUSTOM_SLOT),
        ),
        max_attempts=1,
    )

    with pytest.raises(
        ApiKeyNotFoundError,
        match=r"OPENROUTER_BACKUP_CREDENTIAL.*openrouter.*\(ID: 3\)",
    ) as exc_info:
        router.query("Summarize the release notes.")

    error = exc_info.value
    assert (error.key_name, error.provider, int(error.key_id)) == (
        CUSTOM_ENV_NAME,
        PROVIDER.value,
        CUSTOM_SLOT,
    )
    frame_names = [entry.name for entry in exc_info.traceback]
    assert "candidates" in frame_names


@pytest.mark.verifies("REQ_CREDENTIAL_RESOLUTION[revision==1]")
def test_fixed_candidate_uses_convention_name_for_unmapped_slot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unmapped fixed slot resolves through its convention env name."""
    unmapped_slot = 7
    convention_name = f"{PROVIDER.name}_API_KEY_{unmapped_slot}"
    monkeypatch.delenv(convention_name, raising=False)
    router = LLMRouter(
        RouterProfile(
            model=Model.DEEPSEEK_V3,
            provider=PROVIDER,
            key_id=GatedSlot(unmapped_slot),
        ),
        max_attempts=1,
    )

    with pytest.raises(
        ApiKeyNotFoundError,
        match=r"OPENROUTER_API_KEY_7.*\(ID: 7\)",
    ) as exc_info:
        router.query("Summarize the release notes.")

    error = exc_info.value
    assert (error.key_name, error.provider, int(error.key_id)) == (
        convention_name,
        PROVIDER.value,
        unmapped_slot,
    )
