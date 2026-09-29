# mutation-pin: REQ_CONFIG_INSTALLATION_COHERENCE SM-F91AFA31
# pinned-by: claude-opus-5-5
from __future__ import annotations

import dataclasses

import pytest

import llm_router as package
from llm_router._internal.providers import registry

pytestmark = pytest.mark.verification_kind("unit")


@pytest.mark.verifies("REQ_CONFIG_INSTALLATION_COHERENCE[revision==2]")
def test_install_config_is_active_before_adapter_caches_are_cleared(
    monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> None:
    current = package.get_config()
    request.addfinalizer(lambda: package.install_config(current))
    new_defaults = dataclasses.replace(
        current.defaults,
        structured_output_max_attempts=current.structured_output_max_attempts + 1,
    )
    new_config = dataclasses.replace(current, defaults=new_defaults)
    seen: list[object] = []
    original = registry.clear_adapter_caches

    def wrapped() -> None:
        original()
        seen.append(package.get_config())

    monkeypatch.setattr(registry, "clear_adapter_caches", wrapped)

    package.install_config(new_config)

    assert seen
    assert seen[0] is new_config
    assert package.get_config() is new_config
