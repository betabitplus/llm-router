"""Minimal public package smoke tests."""

from __future__ import annotations

import importlib
import sys
from dataclasses import replace
from types import ModuleType

import pytest

import llm_router as package
from llm_router import LLMRouterConfig
from tests.llm_router.support.fault_observation import retain_local_fault_injection

_PUBLIC_API_CONTRACT = "REQ_PUBLIC_API_SURFACE"


def _public_surface_issues(module: ModuleType) -> set[str]:
    declared = list(getattr(module, "__all__", []))
    issues: set[str] = set()
    if not declared:
        issues.add("<empty-public-surface>")
    issues.update(name for name in declared if not hasattr(module, name))
    return issues


@pytest.mark.verifies("REQ_PUBLIC_API_SURFACE[revision==1]")
@pytest.mark.coverage_item("VC_PUBLIC_API_ROOT_EXPORTS")
@pytest.mark.verification_kind("unit")
def test_declared_public_api_resolves() -> None:
    previous_package = sys.modules.pop("llm_router", None)
    try:
        reloaded = importlib.import_module("llm_router")
        assert reloaded.__version__
        assert not _public_surface_issues(reloaded)
    finally:
        if previous_package is not None:
            sys.modules["llm_router"] = previous_package


@pytest.mark.verifies("REQ_CONFIG_INSTALLATION_COHERENCE[revision==2]")
@pytest.mark.coverage_item("VC_CONFIG_INSTALLATION_ROUND_TRIP")
@pytest.mark.verification_kind("unit")
def test_public_config_lifecycle_round_trips_replacement_snapshot() -> None:
    config = package.get_config()
    replacement = replace(config, default_key_id=config.default_key_id + 1)

    assert isinstance(replacement, LLMRouterConfig)
    assert replacement is not config
    assert package.install_config(replacement) is replacement
    assert package.get_config() is replacement


@pytest.mark.verifies("REQ_PUBLIC_API_SURFACE[revision==1]")
@pytest.mark.fault_item(_PUBLIC_API_CONTRACT, "architecture.layer-bypass")
@pytest.mark.verification_kind("unit")
def test_public_api_oracle_detects_missing_root_export(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delattr(package, "LLMRouter")
    retain_local_fault_injection(
        contract_id=_PUBLIC_API_CONTRACT,
        fault_class="architecture.layer-bypass",
        mechanism="remove-package-root-export",
        details={"symbol": "LLMRouter"},
    )

    assert _public_surface_issues(package) == {"LLMRouter"}


@pytest.mark.verifies("REQ_PUBLIC_API_SURFACE[revision==1]")
@pytest.mark.fault_item(_PUBLIC_API_CONTRACT, "spec.wrong-outcome")
@pytest.mark.verification_kind("unit")
def test_public_api_oracle_detects_empty_declared_surface(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(package, "__all__", [])
    retain_local_fault_injection(
        contract_id=_PUBLIC_API_CONTRACT,
        fault_class="spec.wrong-outcome",
        mechanism="empty-declared-public-surface",
    )

    assert _public_surface_issues(package) == {"<empty-public-surface>"}


@pytest.mark.verifies("REQ_PUBLIC_API_SURFACE[revision==1]")
@pytest.mark.fault_item(_PUBLIC_API_CONTRACT, "spec.missing-partition")
@pytest.mark.verification_kind("unit")
def test_public_api_oracle_detects_unresolved_declared_partition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missing_symbol = "__fault_missing_public_partition__"
    monkeypatch.setattr(package, "__all__", [*package.__all__, missing_symbol])
    retain_local_fault_injection(
        contract_id=_PUBLIC_API_CONTRACT,
        fault_class="spec.missing-partition",
        mechanism="add-unresolved-public-partition",
        details={"symbol": missing_symbol},
    )

    assert _public_surface_issues(package) == {missing_symbol}
