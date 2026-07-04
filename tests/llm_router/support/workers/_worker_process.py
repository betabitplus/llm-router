"""Private subprocess helpers for llm_router support workers.

Why:
    Keeps repeated subprocess invocation, repo-root env shaping, and JSON
    result parsing in one place for llm_router e2e support modules.

When to use:
    Import from here when a llm_router support module runs a worker via
    `python -m ...` and expects one JSON object on stdout.

How:
    Use `run_worker_module(...)` from runner modules and `ensure_worker_env()`
    inside worker entrypoints before importing project code.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Sequence
from typing import Any

from tests.support.paths import get_repo_root

REPO_ROOT = get_repo_root()


# ================================================================================
# Public API
# ================================================================================


def run_worker_module(
    *,
    module: str,
    args: Sequence[str],
    missing_output_message: str,
) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
    """Run one worker module and parse the last non-empty stdout line as JSON."""
    cmd = [
        sys.executable,
        "-m",
        module,
        *args,
    ]
    completed = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=_worker_env(),
    )
    payload = parse_worker_json_output(
        stdout=completed.stdout,
        missing_output_message=missing_output_message,
    )
    return completed, payload


def ensure_worker_env() -> None:
    """Ensure worker subprocesses can import the repository package tree."""
    os.environ["PYTHONPATH"] = _build_pythonpath(os.environ.get("PYTHONPATH"))


def parse_worker_json_output(
    *,
    stdout: str,
    missing_output_message: str,
) -> dict[str, Any]:
    """Parse the last non-empty stdout line from a worker as one JSON object."""
    lines = [line for line in stdout.splitlines() if line.strip()]
    if not lines:
        raise AssertionError(missing_output_message)
    return json.loads(lines[-1])


# ================================================================================
# Internal Helpers
# ================================================================================


def _worker_env() -> dict[str, str]:
    return {
        **dict(os.environ),
        "PYTHONPATH": _build_pythonpath(os.environ.get("PYTHONPATH")),
    }


def _build_pythonpath(existing: str | None) -> str:
    repo_root = str(REPO_ROOT)
    if not existing:
        return repo_root

    entries = existing.split(os.pathsep)
    if repo_root in entries:
        return existing
    return os.pathsep.join([repo_root, *entries])
