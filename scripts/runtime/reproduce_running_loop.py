#!/usr/bin/env python3
"""Run a module inside an already-running asyncio event loop.

Why:
    Reproduces notebook-style execution semantics such as VS Code Interactive,
    where a module runs while an event loop is already active.

When to use:
    Run this script from the terminal and pass a workbench module path to
    verify that the module behaves the same way it would under an interactive
    running-loop environment.

Examples:
    uv run python scripts/runtime/reproduce_running_loop.py \
        workbench.<package>.<provider>.<script>
"""

from __future__ import annotations

import argparse
import asyncio
import runpy
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_REPO_ROOT_STR = str(_REPO_ROOT)
if _REPO_ROOT_STR not in sys.path:
    sys.path.insert(0, _REPO_ROOT_STR)


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run a module inside an active asyncio event loop.",
    )
    parser.add_argument(
        "module",
        help="Module path to execute, for example workbench.<package>.<script>.",
    )
    parser.add_argument(
        "module_args",
        nargs=argparse.REMAINDER,
        help="Optional arguments passed through to the target module.",
    )
    return parser.parse_args()


async def _run_module_in_loop(module: str, module_args: list[str]) -> None:
    """Execute one module while an event loop is already running."""
    original_argv = sys.argv[:]
    sys.argv = [module, *module_args]
    try:
        runpy.run_module(module, run_name="__main__")
    finally:
        sys.argv = original_argv


def main() -> None:
    """Run the requested module inside a running loop."""
    args = _parse_args()
    asyncio.run(_run_module_in_loop(args.module, args.module_args))


if __name__ == "__main__":
    main()
