"""llm-router provider-boundary configuration for the shared scripted HTTP server."""

from __future__ import annotations

from typing import Self

from py_lib_testkit import (
    RequestRecord,
    ScriptedHTTPServer as _ScriptedHTTPServer,
    ScriptedResponse,
    evidence,
)

__all__ = ["RequestRecord", "ScriptedHTTPServer", "ScriptedResponse"]


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
