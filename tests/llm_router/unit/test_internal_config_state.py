from __future__ import annotations

from dataclasses import replace

import pytest

import llm_router as package
from llm_router._internal.runtime.router import RouterRuntime

pytestmark = [
    pytest.mark.verifies("REQ_CONFIG_INSTALLATION_COHERENCE[revision==2]"),
    pytest.mark.verification_kind("unit"),
]


@pytest.mark.coverage_item("VC_CONFIG_INSTALLATION_RUNTIME_CAPTURE")
def test_runtime_constructed_after_install_uses_replacement_snapshot() -> None:
    current = package.get_config()
    replacement = replace(current, default_key_id=current.default_key_id + 1)

    package.install_config(replacement)
    runtime = RouterRuntime(spec=replacement.default_model)

    assert runtime.config is replacement
