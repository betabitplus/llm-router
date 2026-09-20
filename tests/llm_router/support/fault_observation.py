"""Retained local fault observations for deterministic non-provider challenges."""

from __future__ import annotations

from py_lib_testkit import evidence

__all__ = ["retain_local_fault_injection"]


def retain_local_fault_injection(
    *,
    contract_id: str,
    fault_class: str,
    mechanism: str,
    details: dict[str, object] | None = None,
) -> None:
    """Retain one explicit local fault challenge without claiming an HTTP producer."""
    evidence.observation(
        "Local fault injection",
        kind="fault-injection",
        payload={
            "contract_id": contract_id,
            "fault_class": fault_class,
            "mechanism": mechanism,
            "details": details or {},
        },
    )
