"""Root pytest configuration for reusable test infrastructure.

Why:
    Keeps repository-wide pytest setup independent from the product package so
    this file can remain a portable backbone for future libraries.

When to use:
    Put only generic pytest hooks and fixtures here. Package-specific fixtures
    belong under the package test tree, for example `tests/<package>/`.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from py_lib_testkit import evidence


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _set_user_property(item: pytest.Item, name: str, value: str) -> None:
    item.user_properties[:] = [
        (key, existing) for key, existing in item.user_properties if key != name
    ]
    item.user_properties.append((name, value))


def pytest_sessionstart(session: pytest.Session) -> None:
    """Snapshot exact verification inputs before the retained pytest run starts."""
    if hasattr(session.config, "workerinput"):
        return
    root = Path(session.config.rootpath)
    destination = Path(
        os.environ.get(
            "TERNFORGE_EVIDENCE_RUN_INPUTS",
            str(root / "test-results/evidence-run-inputs.json"),
        )
    )
    if not destination.is_absolute():
        destination = root / destination

    paths: set[Path] = set()
    input_scope = (
        "src/llm_router/**/*.py",
        "tests/**/*.py",
        "tests/**/*.feature",
        "features/**/*.feature",
        "docs/requirements/**/*.md",
        "docs/verification-profiles/**/*.md",
    )
    for pattern in input_scope:
        paths.update(path for path in root.glob(pattern) if path.is_file())
    explicit_inputs = ("pyproject.toml", "tests/conftest.py", "docs/test-plan.md")
    for relative in explicit_inputs:
        path = root / relative
        if path.is_file():
            paths.add(path)

    git_executable = shutil.which("git")
    if git_executable is None:
        git_head = "UNKNOWN"
    else:
        try:
            git_head = subprocess.check_output(
                [git_executable, "rev-parse", "HEAD"], cwd=root, text=True
            ).strip()
        except (OSError, subprocess.CalledProcessError):
            git_head = "UNKNOWN"

    inputs = {
        _relative(root, path): _sha256(path)
        for path in sorted(paths, key=lambda value: value.as_posix())
    }
    input_set_sha256 = hashlib.sha256(
        json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    payload = {
        "schema": "ternforge-retained-execution-inputs-1",
        "captured_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "git_head": git_head,
        "input_scope": list(input_scope),
        "explicit_inputs": list(explicit_inputs),
        "input_set_sha256": input_set_sha256,
        "inputs": inputs,
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item: pytest.Item) -> Iterator[None]:
    """Retain exact VCR replay activity while the Allure test call is active."""
    yield
    cassette = item.funcargs.get("vcr")
    if cassette is None:
        return
    play_count = int(getattr(cassette, "play_count", 0) or 0)
    evidence.producer("PRODUCER_VCR")
    evidence.observation(
        "VCR replay boundary interaction",
        kind="external-replay",
        payload={
            "producer": "VCR",
            "producer_id": "PRODUCER_VCR",
            "boundary": "provider-http",
            "interaction": "replay",
            "mode": "vcr-replay",
            "transport": "HTTP",
            "target": "historical-live-provider",
            "play_count": play_count,
            "all_played": bool(getattr(cassette, "all_played", False)),
        },
    )


def pytest_runtest_setup(item: pytest.Item) -> None:
    """Retain semantic binding and exact test-source identity in JUnit."""
    coverage_markers = list(item.iter_markers(name="coverage_item"))
    if not coverage_markers:
        return
    for marker in coverage_markers:
        if marker.args:
            _set_user_property(item, "coverage_item", str(marker.args[0]))
            break

    source = Path(item.path)
    root = Path(item.config.rootpath)
    _set_user_property(item, "source_path", _relative(root, source))
    _set_user_property(item, "source_sha256", _sha256(source))
