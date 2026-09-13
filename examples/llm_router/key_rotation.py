"""Rotate API keys automatically
=============================

Set ``key_id="auto"`` once, then keep making normal requests. This example isolates
key selection and limiter behavior behind a deterministic localhost endpoint, so it
needs no provider credentials and makes no claim about live-provider fidelity.
"""
# sphinx_gallery_tags = ["routing", "keys", "limits"]
# sphinx_gallery_thumbnail_path = "_static/gallery/key-rotation.svg"

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import ClassVar

from llm_router import (
    LLMRouter,
    Model,
    Provider,
    ProviderLimits,
    RouterProfile,
    get_config,
    install_config,
)

_ROTATING_KEY_COUNT = 2

_original_config = get_config()
_server: ThreadingHTTPServer | None = None
_server_thread: Thread | None = None
_previous_demo_keys: dict[str, str | None] = {}


class _DemoEndpoint(BaseHTTPRequestHandler):
    """Minimal OpenAI-compatible endpoint used only by this runnable example."""

    protocol_version = "HTTP/1.1"
    authorizations: ClassVar[list[str]] = []

    def do_POST(self) -> None:
        """Accept one chat completion and retain only the authorization identity."""
        content_length = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(content_length)
        self.authorizations.append(self.headers.get("Authorization", ""))
        payload = json.dumps(
            {
                "id": "chatcmpl-key-rotation-demo",
                "object": "chat.completion",
                "created": 0,
                "model": "demo",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "ok"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 1,
                    "completion_tokens": 1,
                    "total_tokens": 2,
                },
            }
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(payload)

    def log_request(self, code: int | str = "-", size: int | str = "-") -> None:
        """Keep the documentation output focused on router behavior."""


# %%
# Configure automatic key selection
# ---------------------------------
# Two distinct demo credentials are mapped through the same public provider config
# used for real deployments. The endpoint is local on purpose: this page demonstrates
# key rotation and per-key limiting, while provider fidelity is covered separately by
# live/experiment evidence.
if __name__ == "__main__":
    demo_key_names = ("TERNFORGE_DEMO_KEY_1", "TERNFORGE_DEMO_KEY_2")
    _previous_demo_keys = {name: os.environ.get(name) for name in demo_key_names}
    os.environ[demo_key_names[0]] = "demo-key-one"
    os.environ[demo_key_names[1]] = "demo-key-two"

    _DemoEndpoint.authorizations.clear()
    _server = ThreadingHTTPServer(("127.0.0.1", 0), _DemoEndpoint)
    _server_thread = Thread(target=_server.serve_forever, daemon=True)
    _server_thread.start()

    providers = dict(_original_config.catalog.providers)
    providers[Provider.OPENROUTER] = replace(
        providers[Provider.OPENROUTER],
        api_key_env_vars={1: demo_key_names[0], 2: demo_key_names[1]},
    )
    provider_base_urls = dict(_original_config.catalog.provider_base_urls)
    provider_base_urls[Provider.OPENROUTER] = (
        f"http://127.0.0.1:{_server.server_address[1]}/v1"
    )
    install_config(
        replace(
            _original_config,
            catalog=replace(
                _original_config.catalog,
                providers=providers,
                provider_base_urls=provider_base_urls,
            ),
        )
    )

    router = LLMRouter(
        RouterProfile(
            provider=Provider.OPENROUTER,
            model=Model.DEEPSEEK_V3,
            key_id="auto",
        ),
        limits_by_provider={
            Provider.OPENROUTER: ProviderLimits(
                rps=0.5,
                rpm=1_000_000_000,
                cooldown_seconds=0.0,
                cooldown_after_failures=0,
            )
        },
        temperature=0.0,
        seed=42,
        attempt_timeout_seconds=5.0,
    )

# %%
# Send repeated requests
# ----------------------
# ``aquery()`` stays identical across calls. Only the selected key and any limiter
# wait change. The endpoint records the Authorization header only long enough to
# confirm that the first two HTTP requests used different credentials.
if __name__ == "__main__":

    async def run_requests() -> None:
        """Send three requests and summarize automatic key selection."""
        key_labels: dict[int, str] = {}
        for number in range(1, 4):
            response = await router.aquery("Reply with ok.")
            attempt = response.routing_trace[-1]
            key_label = key_labels.setdefault(
                attempt.key_id, f"key-{len(key_labels) + 1}"
            )
            print(f"{number}. key={key_label} wait={attempt.wait_seconds:.2f}s")

        first_rotation = _DemoEndpoint.authorizations[:_ROTATING_KEY_COUNT]
        distinct = len(set(first_rotation)) == _ROTATING_KEY_COUNT
        print(f"distinct HTTP credentials observed={distinct}")

    try:
        asyncio.run(run_requests())
    finally:
        install_config(_original_config)
        if _server is not None:
            _server.shutdown()
            _server.server_close()
        if _server_thread is not None:
            _server_thread.join()
        for name, previous in _previous_demo_keys.items():
            if previous is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = previous

# %%
# The first two requests select different key slots; the third cycles back to
# ``key-1``. ``wait`` shows whether limiter spacing was needed before that reuse.
