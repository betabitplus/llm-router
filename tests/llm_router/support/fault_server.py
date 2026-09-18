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
]


class ProviderSentinelHTTPServer(_ScriptedHTTPServer):
    """Local HTTP sentinel measuring forbidden calls without claiming substitute use."""


class ScriptedHTTPServer(_ScriptedHTTPServer):
    """Shared scripted HTTP server configured as an llm-router provider substitute."""

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
