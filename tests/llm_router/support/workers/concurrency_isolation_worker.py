"""Subprocess worker for concurrency-isolation llm_router e2e tests.

Why:
    Keeps shared async-client concurrency behavior out of the main pytest
    process so isolation can be tested through the public API.

When to use:
    Use only via
    `tests.llm_router.support.workers.concurrency_isolation.run_concurrency_isolation_worker()`.

How:
    Start a local body-aware HTTP server, patch the external OpenAI SDK before
    importing `llm_router`, then execute two concurrent `aquery(...)` calls with
    separate sessions in one process.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import socket
import threading
import time
from contextlib import AbstractContextManager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from tests.llm_router.support.workers.worker_patches import patch_openai


def _openai_payload(*, text: str) -> bytes:
    """Return a minimal OpenAI-compatible success payload."""
    return json.dumps(
        {
            "id": f"chatcmpl-{text}",
            "object": "chat.completion",
            "created": 0,
            "model": "local-model",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": text},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 12,
                "completion_tokens": 5,
                "total_tokens": 17,
            },
        }
    ).encode("utf-8")


class _ConcurrencyServer(ThreadingHTTPServer):
    """Body-aware local server for concurrent OpenAI-compatible requests."""

    daemon_threads = True
    block_on_close = False
    allow_reuse_address = True

    def __init__(self, server_address: tuple[str, int]) -> None:
        super().__init__(server_address, _ConcurrencyHandler)
        self.request_count = 0
        self._lock = threading.Lock()

    def record_request(self) -> None:
        """Increment the request counter."""
        with self._lock:
            self.request_count += 1


class _ConcurrencyHandler(BaseHTTPRequestHandler):
    """Handler that chooses response text from the request body."""

    server: _ConcurrencyServer

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/v1/chat/completions":
            self.send_response(404)
            self.end_headers()
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length)
        body_text = body.decode("utf-8", errors="ignore")
        self.server.record_request()

        time.sleep(0.05)
        if "ALPHA" in body_text:
            payload = _openai_payload(text="ALPHA")
        elif "BETA" in body_text:
            payload = _openai_payload(text="BETA")
        else:
            payload = _openai_payload(text="UNKNOWN")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        _ = format
        _ = args


class BodyAwareServer(AbstractContextManager["BodyAwareServer"]):
    """Context-managed body-aware local server."""

    def __init__(self, *, port: int) -> None:
        self._port = port
        self._server: _ConcurrencyServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def base_url(self) -> str:
        """Return the server base URL."""
        return f"http://127.0.0.1:{self._port}"

    @property
    def request_count(self) -> int:
        """Return how many requests were served."""
        if self._server is None:
            return 0
        return self._server.request_count

    def __enter__(self) -> BodyAwareServer:
        self._server = _ConcurrencyServer(("127.0.0.1", self._port))
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name=f"concurrency-server-{self._port}",
            daemon=True,
        )
        self._thread.start()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        _ = exc_type
        _ = exc
        _ = tb
        if self._server is not None:
            server = self._server
            shutdown_thread = threading.Thread(
                target=server.shutdown,
                name=f"concurrency-server-shutdown-{self._port}",
                daemon=True,
            )
            shutdown_thread.start()
            self._wakeup(server)
            shutdown_thread.join(timeout=0.05)
            if shutdown_thread.is_alive():
                self._wakeup(server)
            shutdown_thread.join(timeout=5.0)
            server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=5.0)

    @staticmethod
    def _wakeup(server: _ConcurrencyServer) -> None:
        try:
            with socket.create_connection(server.server_address, timeout=0.05):
                return
        except OSError:
            return


async def _run_scenario() -> dict[str, Any]:
    from llm_router import LLMRouter, Model, Provider, RouterProfile, Session

    alpha_session = Session(system="Reply with only the requested marker.")
    beta_session = Session(system="Reply with only the requested marker.")

    alpha_router = LLMRouter(
        RouterProfile(model=Model.DEEPSEEK_V3, provider=Provider.OPENROUTER),
        session=alpha_session,
        temperature=0.0,
        seed=1,
    )
    beta_router = LLMRouter(
        RouterProfile(model=Model.DEEPSEEK_V3, provider=Provider.OPENROUTER),
        session=beta_session,
        temperature=0.0,
        seed=1,
    )

    alpha_response, beta_response = await asyncio.gather(
        alpha_router.aquery("Reply only ALPHA."),
        beta_router.aquery("Reply only BETA."),
    )

    return {
        "ok": True,
        "alpha_text": alpha_response.output_text,
        "beta_text": beta_response.output_text,
        "alpha_history_length": len(alpha_session.history),
        "beta_history_length": len(beta_session.history),
        "alpha_user_parts": [str(part) for part in alpha_session.history[0].parts],
        "beta_user_parts": [str(part) for part in beta_session.history[0].parts],
        "alpha_routing_trace": [
            attempt.model_dump() for attempt in alpha_response.routing_trace
        ],
        "beta_routing_trace": [
            attempt.model_dump() for attempt in beta_response.routing_trace
        ],
    }


def main() -> None:
    _ = argparse.ArgumentParser().parse_args()
    port = 18917

    try:
        with BodyAwareServer(port=port) as server:
            patch_openai(
                forced_base_url=f"{server.base_url}/v1",
                disable_sdk_retries=True,
            )
            result = asyncio.run(_run_scenario())
            result["request_count"] = server.request_count
    except Exception as exc:  # Defensive: worker should always emit JSON.
        result = {
            "ok": False,
            "alpha_text": "",
            "beta_text": "",
            "alpha_history_length": 0,
            "beta_history_length": 0,
            "alpha_user_parts": [],
            "beta_user_parts": [],
            "alpha_routing_trace": [],
            "beta_routing_trace": [],
            "request_count": 0,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        }
    else:
        result["error_type"] = None
        result["error_message"] = None

    print(json.dumps(result))


if __name__ == "__main__":
    main()
