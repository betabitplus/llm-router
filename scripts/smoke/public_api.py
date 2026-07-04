"""Smoke test the supported top-level public export surface."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_REPO_ROOT_STR = str(_REPO_ROOT)
if _REPO_ROOT_STR not in sys.path:
    sys.path.insert(0, _REPO_ROOT_STR)


def main() -> None:
    """Assert that the top-level `__all__` remains internally consistent."""
    from scripts._shared.project_config import get_project_tooling_config

    project_config = get_project_tooling_config()
    package = importlib.import_module(project_config.primary_package)

    exported_names = list(getattr(package, "__all__", []))
    if not exported_names:
        msg = "Package __all__ must not be empty."
        raise RuntimeError(msg)
    if len(exported_names) != len(set(exported_names)):
        msg = "Package __all__ contains duplicate names."
        raise RuntimeError(msg)

    missing_attributes = [name for name in exported_names if not hasattr(package, name)]
    if missing_attributes:
        msg = f"Missing exported attributes: {sorted(missing_attributes)}"
        raise RuntimeError(msg)

    print(f"Public API smoke passed: {len(exported_names)} exports")


if __name__ == "__main__":
    main()
