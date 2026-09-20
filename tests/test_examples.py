"""Offline contract checks for shipped examples."""

from __future__ import annotations

import importlib
import runpy
import socket
import sys
from pathlib import Path
from threading import Thread

import pytest

from llm_router import LLMRouter
from tests.llm_router.support.fault_observation import retain_local_fault_injection

EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples" / "llm_router"


def _example_modules() -> list[str]:
    return [
        f"examples.llm_router.{path.stem}"
        for path in sorted(EXAMPLES_DIR.glob("*.py"))
        if path.name != "__init__.py"
    ]


def _block_live_workflow(*_args: object, **_kwargs: object) -> None:
    msg = "example import attempted to start a live workflow"
    raise AssertionError(msg)


_EXAMPLE_IMPORT_CONTRACT = "REQ_EXAMPLE_IMPORT_SAFETY"


def _install_live_workflow_sentinels(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(socket.socket, "connect", _block_live_workflow)
    monkeypatch.setattr(socket.socket, "bind", _block_live_workflow)
    monkeypatch.setattr(socket, "create_connection", _block_live_workflow)
    monkeypatch.setattr(Thread, "start", _block_live_workflow)
    monkeypatch.setattr(LLMRouter, "query", _block_live_workflow)
    monkeypatch.setattr(LLMRouter, "aquery", _block_live_workflow)


def _missing_example_partitions(selected: list[str]) -> set[str]:
    return set(_example_modules()) - set(selected)


@pytest.mark.hermetic
@pytest.mark.verifies("REQ_EXAMPLE_IMPORT_SAFETY[revision==1]")
@pytest.mark.coverage_item("VC_EXAMPLE_IMPORT_SAFETY")
@pytest.mark.verification_kind("unit")
@pytest.mark.parametrize(
    "module",
    _example_modules(),
    ids=lambda module: module.rsplit(".", maxsplit=1)[-1],
)
@pytest.mark.coverage_path("case-id")
def test_example_import_is_safe(
    module: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Each shipped example executes a fresh import without starting live work."""
    _install_live_workflow_sentinels(monkeypatch)

    sys.modules.pop(module, None)
    previous_package = sys.modules.pop("llm_router", None)
    try:
        importlib.invalidate_caches()
        imported = importlib.import_module(module)
        assert imported.__name__ == module
    finally:
        if previous_package is not None:
            sys.modules["llm_router"] = previous_package


@pytest.mark.hermetic
@pytest.mark.verifies("REQ_EXAMPLE_IMPORT_SAFETY[revision==1]")
@pytest.mark.fault_item(_EXAMPLE_IMPORT_CONTRACT, "impl.control-flow")
@pytest.mark.fault_item(_EXAMPLE_IMPORT_CONTRACT, "interface.unexpected-interaction")
@pytest.mark.fault_item(_EXAMPLE_IMPORT_CONTRACT, "spec.wrong-outcome")
@pytest.mark.verification_kind("unit")
def test_example_import_sentinels_detect_main_guard_bypass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_live_workflow_sentinels(monkeypatch)
    module = "examples.llm_router.multi_route"
    for fault_class in (
        "impl.control-flow",
        "interface.unexpected-interaction",
        "spec.wrong-outcome",
    ):
        retain_local_fault_injection(
            contract_id=_EXAMPLE_IMPORT_CONTRACT,
            fault_class=fault_class,
            mechanism="force-example-main-path",
            details={"module": module},
        )

    sys.modules.pop(module, None)
    with pytest.raises(
        AssertionError, match="example import attempted to start a live workflow"
    ):
        runpy.run_module(module, run_name="__main__")


@pytest.mark.verifies("REQ_EXAMPLE_IMPORT_SAFETY[revision==1]")
@pytest.mark.fault_item(_EXAMPLE_IMPORT_CONTRACT, "spec.missing-partition")
@pytest.mark.verification_kind("unit")
def test_example_partition_oracle_detects_omitted_module() -> None:
    modules = _example_modules()
    omitted = modules[0]
    retain_local_fault_injection(
        contract_id=_EXAMPLE_IMPORT_CONTRACT,
        fault_class="spec.missing-partition",
        mechanism="omit-shipped-example-from-denominator",
        details={"module": omitted},
    )

    assert _missing_example_partitions(modules[1:]) == {omitted}
