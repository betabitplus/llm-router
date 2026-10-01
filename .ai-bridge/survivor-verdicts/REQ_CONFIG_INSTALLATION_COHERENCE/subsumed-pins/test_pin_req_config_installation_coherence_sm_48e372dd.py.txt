# mutation-pin: REQ_CONFIG_INSTALLATION_COHERENCE SM-48E372DD
# pinned-by: claude-opus-5-5
# written-by: claude-sonnet-5-5, the draft author with tools
from __future__ import annotations

import dataclasses
from typing import Any

import pytest

import llm_router as package

pytestmark = pytest.mark.verification_kind("unit")


@pytest.fixture
def restore_config() -> Any:
    original = package.get_config()
    yield original
    package.install_config(original)


@pytest.mark.verifies("REQ_CONFIG_INSTALLATION_COHERENCE[revision==2]")
def test_install_equal_but_distinct_snapshot_becomes_active(
    restore_config: object,
) -> None:
    first = dataclasses.replace(restore_config)
    second = dataclasses.replace(restore_config)
    assert first is not second
    assert first == second

    assert package.install_config(first) is first
    assert package.get_config() is first

    assert package.install_config(second) is second
    assert package.get_config() is second
