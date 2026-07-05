"""Shared setup for runnable llm_router e2e modules.

Why:
    Centralizes manual e2e execution setup at the e2e package level.

When to use:
    Imported automatically when running e2e scenarios in module mode, for
    example `uv run python -m tests.llm_router.e2e.provider_sdk_wrapping.test_example`.
"""

from __future__ import annotations

import sys
from pathlib import Path

from py_lib_tooling import configure_direct_module_process

configure_direct_module_process(
    main_file=getattr(sys.modules.get("__main__"), "__file__", None),
    package_root=Path(__file__).resolve().parent,
    configure_logging_from_env="LLM_ROUTER_LOG_LEVEL",
)
