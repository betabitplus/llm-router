# mutation-pin: REQ_CONFIG_INSTALLATION_COHERENCE SM-39305DEA
# pinned-by: claude-opus-5-5
from __future__ import annotations

import dataclasses

import pytest

import llm_router as package
from llm_router._internal.providers import registry

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_CONFIG_INSTALLATION_COHERENCE[revision==2]")
def test_install_config_is_active_before_adapter_caches_clear(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = package.get_config()
    defaults = dataclasses.replace(
        original.defaults,
        structured_output_max_attempts=(original.structured_output_max_attempts + 1),
    )
    replacement = dataclasses.replace(original, defaults=defaults)
    real_clear = registry.clear_adapter_caches
    seen: list[object] = []

    def wrapped_clear() -> None:
        seen.append(package.get_config())
        real_clear()

    monkeypatch.setattr(registry, "clear_adapter_caches", wrapped_clear)
    try_install = package.install_config
    result = try_install(replacement)
    monkeypatch.undo()
    try_install(original)

    assert result is replacement
    assert seen == [replacement]
