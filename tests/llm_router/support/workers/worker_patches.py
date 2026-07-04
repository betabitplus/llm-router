"""Shared SDK patching for hermetic fault-injected llm_router e2e workers.

Why:
    Keeps provider SDK redirection in one place so fault-injected subprocess
    workers can share the same public-API-only setup.

When to use:
    Use from worker modules that need to steer real SDK traffic to a local
    scripted server without changing `src/`.

How:
    Call `prepare_fault_case(...)` before importing and using `llm_router`.
"""

from __future__ import annotations

import importlib
import os
import sys
import tempfile
import types
from contextlib import contextmanager, suppress
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

# ================================================================================
# Provider Patchers
# ================================================================================


def patch_openai(*, forced_base_url: str | None, disable_sdk_retries: bool) -> None:
    """Patch OpenAI SDK clients to use a forced local base URL."""
    import openai

    original_sync = openai.OpenAI
    original_async = openai.AsyncOpenAI

    class PatchedOpenAI(original_sync):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            if forced_base_url is not None:
                kwargs["base_url"] = forced_base_url
            if disable_sdk_retries:
                kwargs["max_retries"] = 0
            super().__init__(*args, **kwargs)

    class PatchedAsyncOpenAI(original_async):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            if forced_base_url is not None:
                kwargs["base_url"] = forced_base_url
            if disable_sdk_retries:
                kwargs["max_retries"] = 0
            super().__init__(*args, **kwargs)

    openai.OpenAI = PatchedOpenAI
    openai.AsyncOpenAI = PatchedAsyncOpenAI


@contextmanager
def patched_openai_sdk(*, forced_base_url: str | None, disable_sdk_retries: bool):
    """Temporarily patch the OpenAI SDK client classes.

    This is useful for in-process e2e tests that want hermetic SDK redirection
    without leaving global module state mutated for subsequent tests.
    """
    import openai

    original_sync = openai.OpenAI
    original_async = openai.AsyncOpenAI

    patch_openai(
        forced_base_url=forced_base_url,
        disable_sdk_retries=disable_sdk_retries,
    )
    try:
        yield
    finally:
        openai.OpenAI = original_sync
        openai.AsyncOpenAI = original_async


def patch_google_genai(*, server_base_url: str) -> None:
    """Patch Google GenAI client construction to point at a local server."""
    from google import genai as genai_pkg
    from google.genai import client as genai_client_module

    original_client = genai_client_module.Client

    class PatchedClient(original_client):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            http_options = dict(kwargs.pop("http_options", {}))
            http_options.setdefault("baseUrl", server_base_url)
            http_options.setdefault("apiVersion", "v1beta")
            kwargs["http_options"] = http_options
            super().__init__(*args, **kwargs)

    genai_pkg.Client = PatchedClient
    genai_client_module.Client = PatchedClient


@contextmanager
def patched_google_genai_sdk(*, server_base_url: str):
    """Temporarily patch Google GenAI client construction to point at a local server."""
    from google import genai as genai_pkg
    from google.genai import client as genai_client_module

    original_pkg_client = genai_pkg.Client
    original_module_client = genai_client_module.Client

    patch_google_genai(server_base_url=server_base_url)

    try:
        yield
    finally:
        genai_pkg.Client = original_pkg_client
        genai_client_module.Client = original_module_client


def patch_gemini_webapi(*, server_base_url: str) -> None:
    """Patch gemini_webapi dependency modules to use local endpoints."""
    fake_browser_cookie3 = types.ModuleType("browser_cookie3")

    def opera(*, cookie_file: str, domain_name: str) -> list[SimpleNamespace]:
        _ = cookie_file
        _ = domain_name
        return [
            SimpleNamespace(name="__Secure-1PSID", value="local-1psid"),
            SimpleNamespace(name="__Secure-1PSIDTS", value="local-1psidts"),
            SimpleNamespace(name="NID", value="local-nid"),
        ]

    fake_browser_cookie3.opera = opera
    sys.modules["browser_cookie3"] = fake_browser_cookie3

    gemini_client_module = importlib.import_module("gemini_webapi.client")
    gemini_constants = importlib.import_module("gemini_webapi.constants")
    get_access_token_module = importlib.import_module(
        "gemini_webapi.utils.get_access_token"
    )
    upload_file_module = importlib.import_module("gemini_webapi.utils.upload_file")

    endpoints = SimpleNamespace(
        GOOGLE=f"{server_base_url}/google",
        INIT=f"{server_base_url}/app",
        GENERATE=(
            f"{server_base_url}"
            "/_/BardChatUi/data/assistant.lamda.BardFrontendService/StreamGenerate"
        ),
        ROTATE_COOKIES=f"{server_base_url}/RotateCookies",
        UPLOAD=f"{server_base_url}/upload",
        BATCH_EXEC=f"{server_base_url}/_/BardChatUi/data/batchexecute",
    )
    gemini_constants.Endpoint = endpoints
    gemini_client_module.Endpoint = endpoints
    get_access_token_module.Endpoint = endpoints
    upload_file_module.Endpoint = endpoints

    fd, path = tempfile.mkstemp(prefix="llm_router_retry_cookie_", suffix=".sqlite3")
    os.close(fd)
    os.environ["LLM_ROUTER_OPERA_COOKIE_FILE"] = path


@contextmanager
def patched_gemini_webapi_sdk(*, server_base_url: str):
    """Temporarily patch gemini_webapi modules to use local endpoints.

    This mirrors the subprocess-only `patch_gemini_webapi(...)` setup, but
    restores module globals and environment variables on exit so hermetic
    e2e tests can run in-process without leaking state.
    """

    previous_browser_cookie3 = sys.modules.get("browser_cookie3")
    previous_cookie_file = os.environ.get("LLM_ROUTER_OPERA_COOKIE_FILE")

    gemini_client_module = importlib.import_module("gemini_webapi.client")
    gemini_constants = importlib.import_module("gemini_webapi.constants")
    get_access_token_module = importlib.import_module(
        "gemini_webapi.utils.get_access_token"
    )
    upload_file_module = importlib.import_module("gemini_webapi.utils.upload_file")

    previous_endpoints: list[tuple[object, str, object | None, bool]] = []
    for module_obj in (
        gemini_constants,
        gemini_client_module,
        get_access_token_module,
        upload_file_module,
    ):
        attr = "Endpoint"
        had_attr = hasattr(module_obj, attr)
        old_value = getattr(module_obj, attr, None)
        previous_endpoints.append((module_obj, attr, old_value, had_attr))

    patched_cookie_file: str | None = None
    try:
        patch_gemini_webapi(server_base_url=server_base_url)
        patched_cookie_file = os.environ.get("LLM_ROUTER_OPERA_COOKIE_FILE")
        yield
    finally:
        for module_obj, attr, old_value, had_attr in previous_endpoints:
            if had_attr:
                setattr(module_obj, attr, old_value)
            else:
                with suppress(AttributeError):
                    delattr(module_obj, attr)

        if previous_browser_cookie3 is None:
            sys.modules.pop("browser_cookie3", None)
        else:
            sys.modules["browser_cookie3"] = previous_browser_cookie3

        if previous_cookie_file is None:
            os.environ.pop("LLM_ROUTER_OPERA_COOKIE_FILE", None)
        else:
            os.environ["LLM_ROUTER_OPERA_COOKIE_FILE"] = previous_cookie_file

        try:
            if (
                patched_cookie_file
                and patched_cookie_file != previous_cookie_file
                and Path(patched_cookie_file).exists()
            ):
                Path(patched_cookie_file).unlink()
        except OSError:
            pass


# ================================================================================
# Public API
# ================================================================================


def install_fast_worker_runtime_config() -> None:
    """Install fast retry and limiter defaults for hermetic worker processes."""
    from llm_router import (
        BehaviorDefaults,
        ProviderLimits,
        get_config,
        install_config,
    )

    base_config = get_config()
    fast_retry_policy = replace(
        base_config.retry_policy,
        min_wait_seconds=0.01,
        max_wait_seconds=0.02,
    )
    fast_provider_limits = ProviderLimits(
        rps=1_000_000.0,
        rpm=1_000_000_000.0,
        cooldown_seconds=0.0,
        cooldown_after_failures=0,
    )
    fast_limits_by_provider = dict.fromkeys(
        base_config.catalog.providers,
        fast_provider_limits,
    )
    fast_defaults = BehaviorDefaults(
        retry_policy=fast_retry_policy,
        policy=base_config.policy,
        default_max_tool_rounds=base_config.default_max_tool_rounds,
        structured_output_max_attempts=base_config.structured_output_max_attempts,
        provider_limits=fast_provider_limits,
        limits_by_provider=fast_limits_by_provider,
    )
    install_config(replace(base_config, defaults=fast_defaults))


def install_worker_provider_base_url(*, provider: str, base_url: str) -> None:
    """Install one provider base URL override for a hermetic worker process."""
    from llm_router import Provider, get_config, install_config

    resolved_provider = Provider(provider)
    base_config = get_config()
    provider_base_urls = dict(base_config.provider_base_urls)
    provider_base_urls[resolved_provider] = base_url
    catalog = replace(base_config.catalog, provider_base_urls=provider_base_urls)
    install_config(replace(base_config, catalog=catalog))


def prepare_fault_case(*, case: str, server_base_url: str) -> None:
    """Apply env setup and SDK patching for one hermetic worker case."""
    if case == "openai":
        os.environ.setdefault("OPENROUTER_API_KEY_1", "LOCAL_RETRY_KEY")
        patch_openai(
            forced_base_url=f"{server_base_url}/v1",
            disable_sdk_retries=True,
        )
        return

    if case == "google":
        os.environ.setdefault("GOOGLE_API_KEY_1", "LOCAL_RETRY_KEY")
        patch_google_genai(server_base_url=server_base_url)
        return

    if case == "qwenchat":
        os.environ.setdefault("QWENCHAT_API_KEY_1", "LOCAL_RETRY_KEY")
        install_worker_provider_base_url(
            provider="qwenchat",
            base_url=f"{server_base_url}/api",
        )
        return

    if case == "aistudio_nonvideo":
        os.environ.setdefault("AISTUDIO_API_KEY_1", "LOCAL_RETRY_KEY")
        install_worker_provider_base_url(
            provider="aistudio",
            base_url=f"{server_base_url}/v1",
        )
        patch_openai(forced_base_url=None, disable_sdk_retries=True)
        return

    if case == "aistudio_video":
        os.environ.setdefault("AISTUDIO_API_KEY_1", "LOCAL_RETRY_KEY")
        install_worker_provider_base_url(
            provider="aistudio",
            base_url=f"{server_base_url}/v1",
        )
        return

    if case == "gemini_webapi":
        patch_gemini_webapi(server_base_url=server_base_url)
        return

    msg = f"Unknown fault worker case: {case}"
    raise ValueError(msg)
