"""Reusable direct-run and test-process setup helpers.

Why:
    Pytest runs and direct package-module runs need different setup behavior.

When to use:
    Use `configure_pytest_process()` from `tests/conftest.py`.
    Use `configure_direct_module_process(...)` from package `__init__.py`
    files that support direct module execution.

How:
    Pytest setup lowers logging noise.
    Direct module setup enables nested-event-loop support and package-specific
    logging when needed.

Examples:
    configure_pytest_process()
"""

from __future__ import annotations

import asyncio
import importlib
import os
from collections.abc import Awaitable
from pathlib import Path
from typing import TypeVar

from scripts._shared.project_config import get_project_tooling_config

_T = TypeVar("_T")
_PROJECT_CONFIG = get_project_tooling_config()


# ================================================================================
# Public API
# ================================================================================


def run_async(awaitable: Awaitable[_T]) -> _T:
    """Run one coroutine in normal and already-running loop contexts."""
    _apply_nest_asyncio_if_available()
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable)
    return loop.run_until_complete(awaitable)


def configure_pytest_process() -> None:
    """Keep the repo's package logs quiet during pytest runs."""
    logging_module = _import_project_module("._support.logging")
    set_module_log_levels = logging_module.set_module_log_levels

    set_module_log_levels({_PROJECT_CONFIG.primary_package: "WARNING"})


def load_repo_env_file() -> None:
    """Load the shared repo dotenv file into missing environment slots.

    This keeps manual interactive runs closer to `direnv exec .` behavior
    without overriding variables that are already present in the process.
    """
    env_path = _repo_env_file_path()
    if env_path is None or not env_path.is_file():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export "):
            stripped = stripped.removeprefix("export ").strip()
        if "=" not in stripped:
            continue

        key, value = stripped.split("=", 1)
        key = key.strip()
        current_value = os.environ.get(key)
        if not key or (isinstance(current_value, str) and current_value.strip()):
            continue

        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ[key] = value


def configure_direct_module_process(
    *,
    main_file: str | None,
    package_root: Path,
    configure_logging_from_env: str | None = None,
) -> None:
    """Configure one package for direct `python -m ...` execution."""
    if not _main_file_belongs_to_package(
        main_file=main_file,
        package_root=package_root,
    ):
        return

    _apply_nest_asyncio_if_available()
    if configure_logging_from_env is not None:
        logging_module = _import_project_module("._support.logging")
        configure_logging = logging_module.configure_logging

        configure_logging(level=os.getenv(configure_logging_from_env, "DEBUG"))


# ================================================================================
# Runtime Helpers
# ================================================================================


def _apply_nest_asyncio_if_available() -> None:
    """Patch the active event loop in interactive/direct-run environments."""
    try:
        import nest_asyncio
    except ModuleNotFoundError:
        return
    nest_asyncio.apply()


def _main_file_belongs_to_package(*, main_file: str | None, package_root: Path) -> bool:
    """Return whether `main_file` is a real path inside `package_root`."""
    if not isinstance(main_file, str) or not main_file:
        return False

    main_path = Path(main_file).resolve()
    try:
        main_path.relative_to(package_root.resolve())
    except ValueError:
        return False
    return True


def _repo_env_file_path() -> Path | None:
    """Return the shared dotenv path used by the repo when configured."""
    configured = os.getenv(_PROJECT_CONFIG.env_file_var)
    if isinstance(configured, str) and configured.strip():
        return Path(configured).expanduser()
    return Path.home() / "researcher-local" / ".env"


def _import_project_module(module_suffix: str) -> object:
    """Import one module rooted at the repo's primary package."""
    module_name = _PROJECT_CONFIG.primary_package + module_suffix
    return importlib.import_module(module_name)
