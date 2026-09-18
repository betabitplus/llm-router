"""llm-router provider-boundary configuration for the shared scripted HTTP server."""

from __future__ import annotations

from typing import Self

from py_lib_testkit import (
    RequestRecord,
    ScriptedHTTPServer as _ScriptedHTTPServer,
    ScriptedResponse,
    evidence,
)

__all__ = [
    "ProviderSentinelHTTPServer",
    "RequestRecord",
    "ScriptedHTTPServer",
    "ScriptedResponse",
    "retain_fault_injection",
]


def retain_fault_injection(
    *,
    contract_id: str,
    fault_class: str,
    mechanism: str,
    details: dict[str, object] | None = None,
) -> None:
    """Retain one explicit contract-specific fault challenge during the test call."""
    evidence.producer("PRODUCER_SCRIPTED_HTTP_SERVER")
    evidence.observation(
        "Fault injection",
        kind="fault-injection",
        payload={
            "contract_id": contract_id,
            "fault_class": fault_class,
            "mechanism": mechanism,
            "details": details or {},
        },
    )


class ProviderSentinelHTTPServer(_ScriptedHTTPServer):
    """Local HTTP sentinel measuring forbidden calls without claiming substitute use."""


class ScriptedHTTPServer(_ScriptedHTTPServer):
    """Shared scripted HTTP server configured as an llm-router provider substitute."""

    def retain_current_boundary_evidence(self) -> None:
        """Retain provider-substitute and request-journal facts during test call."""
        evidence.producer("PRODUCER_SCRIPTED_HTTP_SERVER")
        evidence.observation(
            "Provider HTTP substitute",
            kind="external-substitute",
            payload={
                "producer": "ScriptedHTTPServer",
                "producer_id": "PRODUCER_SCRIPTED_HTTP_SERVER",
                "boundary": "provider-http",
                "mode": "local-scripted-http",
                "transport": "HTTP",
                "target": "live-provider",
            },
        )
        route_counts = {
            (method, path): self.request_count(method, path)
            for method, path in self._routes
        }
        evidence.observation(
            "Provider HTTP boundary interaction",
            kind="boundary-interaction-check",
            payload={
                "boundary": "provider-http",
                "interaction": "substitute" if sum(route_counts.values()) else "none",
                "requests_received": sum(route_counts.values()),
                "sample_paths": sorted(
                    path for (_, path), count in route_counts.items() if count > 0
                ),
            },
        )

    def __enter__(self) -> Self:
        evidence.observation(
            "Provider HTTP substitute",
            kind="external-substitute",
            payload={
                "producer": "ScriptedHTTPServer",
                "boundary": "provider-http",
                "mode": "local-scripted-http",
                "transport": "HTTP",
                "target": "live-provider",
            },
        )
        super().__enter__()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        """Retain the provider-boundary interaction count before shutdown."""
        route_counts = {
            (method, path): self.request_count(method, path)
            for method, path in self._routes
        }
        evidence.observation(
            "Provider HTTP boundary interaction",
            kind="boundary-interaction-check",
            payload={
                "boundary": "provider-http",
                "requests_received": sum(route_counts.values()),
                "sample_paths": sorted(
                    path for (_, path), count in route_counts.items() if count > 0
                ),
            },
        )
        super().__exit__(exc_type, exc, tb)
