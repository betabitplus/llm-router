"""Subprocess worker for retry-focused llm_router e2e tests.

Why:
    Keeps provider SDK patching out of the main pytest process so retry tests
    can steer real HTTP traffic without mutating library code.

When to use:
    Use only via `tests.llm_router.support.workers.retry.run_retry_worker(...)`.

How:
    Patch provider SDK entry points before importing `llm_router`, then execute
    one public `LLMRouter(...).query(...)` call and print a JSON result.
"""

from __future__ import annotations

import argparse
import json
from typing import Any

from py_lib_tooling import get_test_data_path

from tests.llm_router.support.workers._worker_process import ensure_worker_env
from tests.llm_router.support.workers.worker_patches import (
    install_fast_worker_runtime_config,
    prepare_fault_case,
)

VIDEO_PATH = get_test_data_path("llm_router") / "jumper.mp4"


def _prepare_case(*, case: str, server_base_url: str) -> None:
    prepare_fault_case(case=case, server_base_url=server_base_url)


def _build_router(case: str) -> Any:
    from llm_router import LLMRouter, Model, Provider, RouterProfile, VideoSchema

    if case == "openai":
        return LLMRouter(
            RouterProfile(model=Model.DEEPSEEK_V3, provider=Provider.OPENROUTER),
            temperature=0.0,
            seed=1,
        )

    if case == "google":
        return LLMRouter(
            RouterProfile(model=Model.GEMINI_3_FLASH, provider=Provider.GOOGLE),
            temperature=0.0,
            seed=1,
        )

    if case == "qwenchat":
        return LLMRouter(
            RouterProfile(model=Model.QWEN_MAX_LATEST, provider=Provider.QWENCHAT),
            temperature=0.0,
            seed=1,
        )

    if case == "aistudio_nonvideo":
        return LLMRouter(
            RouterProfile(model=Model.GEMINI_3_FLASH, provider=Provider.AISTUDIO),
            temperature=0.0,
            seed=1,
        )

    if case == "aistudio_video":
        _ = VideoSchema
        return LLMRouter(
            RouterProfile(model=Model.GEMINI_3_FLASH, provider=Provider.AISTUDIO),
            temperature=0.0,
            seed=1,
        )

    if case == "gemini_webapi":
        return LLMRouter(
            RouterProfile(model=Model.GEMINI_FLASH, provider=Provider.GEMINI_WEBAPI),
            temperature=0.0,
            seed=1,
        )

    msg = f"Unknown retry worker case: {case}"
    raise ValueError(msg)


def _build_query_args(case: str, scenario: str) -> tuple[object, dict[str, Any]]:
    from PIL import Image

    from llm_router import VideoSchema

    prompt = "Reply with the retry marker only."

    if case == "aistudio_video":
        return [prompt, VideoSchema(path=str(VIDEO_PATH))], {}

    if case == "gemini_webapi":
        kwargs = {"timeout": 0.05} if scenario == "retryable" else {}
        return prompt, kwargs

    if case == "qwenchat" and scenario in {
        "retryable_upload",
        "non_retryable_upload",
    }:
        image = Image.new("RGB", (2, 2), color=(0, 128, 255))
        return [prompt, image], {}

    return prompt, {}


def _run_case(*, case: str, scenario: str) -> dict[str, Any]:
    router = _build_router(case)
    content, kwargs = _build_query_args(case, scenario)

    try:
        response = router.query(content, **kwargs)
    except Exception as exc:
        return _error_payload(exc)
    return _success_payload(response.output_text)


def _success_payload(output_text: str) -> dict[str, Any]:
    return {
        "ok": True,
        "output_text": output_text,
        "error_type": None,
        "error_message": None,
    }


def _error_payload(exc: Exception) -> dict[str, Any]:
    return {
        "ok": False,
        "output_text": "",
        "error_type": type(exc).__name__,
        "error_message": str(exc),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", required=True)
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--server-base-url", required=True)
    args = parser.parse_args()

    try:
        ensure_worker_env()
        _prepare_case(case=args.case, server_base_url=args.server_base_url)
        if args.scenario in {"retryable", "retryable_upload", "retryable_api_error"}:
            install_fast_worker_runtime_config()
        result = _run_case(case=args.case, scenario=args.scenario)
    except Exception as exc:  # Defensive: worker should always emit JSON.
        result = _error_payload(exc)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
