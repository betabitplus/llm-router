# mutation-pin: REQ_CREDENTIAL_RESOLUTION afe2fe11b15a368c
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

PROVIDER = Provider.MISTRAL
PREFIX = f"{PROVIDER.name}_API_KEY"
BACKUP_ENV = f"{PREFIX}_BACKUP"
BACKUP_SLOT = 2


class RotationEligibleSlot(int):
    """Fixed key slot that a settings layer also marks as rotation-eligible.

    Only ``==`` is customised to accept the automatic-selection marker, while
    ``!=`` keeps plain int semantics. The router therefore lists key candidates
    for it, and candidate listing must still treat it as the fixed slot it is.
    """

    __hash__ = int.__hash__

    def __eq__(self, other: object) -> bool:
        return other == "auto" or int(self) == other


@pytest.mark.verifies("REQ_CREDENTIAL_RESOLUTION[revision==1]")
def test_fixed_slot_candidate_reports_its_custom_env_name_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing fixed slot reports its own configured name, not the default key."""
    for index in range(33):
        monkeypatch.delenv(f"{PREFIX}_{index}", raising=False)
    monkeypatch.delenv(PREFIX, raising=False)
    monkeypatch.delenv(BACKUP_ENV, raising=False)
    config = get_config()
    base_spec = config.catalog.providers[PROVIDER]
    env_names = {**base_spec.api_key_env_vars, BACKUP_SLOT: BACKUP_ENV}
    spec = replace(base_spec, api_key_env_vars=env_names)
    catalog = replace(
        config.catalog,
        providers={**config.catalog.providers, PROVIDER: spec},
    )
    install_config(replace(config, catalog=catalog))
    slot = RotationEligibleSlot(BACKUP_SLOT)
    router = LLMRouter(
        RouterProfile(model=Model.MISTRAL_LARGE, provider=PROVIDER, key_id=slot),
        max_attempts=1,
    )

    with pytest.raises(
        ApiKeyNotFoundError,
        match=r"MISTRAL_API_KEY_BACKUP.*\(ID: 2\)",
    ) as exc_info:
        router.query("Summarize the release notes.")

    error = exc_info.value
    assert error.key_name == BACKUP_ENV
    assert error.provider == PROVIDER.value
    assert int(error.key_id) == BACKUP_SLOT
