"""Reusable path helpers for the test tree.

Why:
    Centralizes repo-relative path lookup for shared test fixtures and manual
    e2e output locations.

When to use:
    Import from here when test infrastructure needs a stable path inside the
    repository or a module-local test-data directory.
"""

from __future__ import annotations

from pathlib import Path

# ================================================================================
# Module Paths
# ================================================================================

TESTS_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = TESTS_DIR.parent


# ================================================================================
# Public API
# ================================================================================


def get_repo_root() -> Path:
    """Return the repository root directory."""
    return REPO_ROOT


def get_test_data_path(module_name: str) -> Path:
    """Return the `tests/<module_name>/data` directory."""
    return TESTS_DIR / module_name / "data"
