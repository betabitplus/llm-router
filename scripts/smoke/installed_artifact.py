"""Smoke test an installed package artifact through the public boundary."""

from __future__ import annotations

import importlib
import sys
from importlib.metadata import packages_distributions, version
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_REPO_ROOT_STR = str(_REPO_ROOT)
if _REPO_ROOT_STR not in sys.path:
    sys.path.insert(0, _REPO_ROOT_STR)


def main() -> None:
    """Assert that the installed artifact resolves to the packaged distribution."""
    from scripts._shared.project_config import get_project_tooling_config

    project_config = get_project_tooling_config()
    package = importlib.import_module(project_config.primary_package)
    package_distribution_names = packages_distributions().get(
        project_config.primary_package,
        [],
    )

    module_path = Path(package.__file__).resolve()
    if "site-packages" not in str(module_path):
        raise RuntimeError(str(module_path))
    if project_config.distribution_name not in package_distribution_names:
        msg = (
            "Installed package import-to-distribution mapping does not include "
            f"{project_config.distribution_name!r}: {package_distribution_names}"
        )
        raise RuntimeError(msg)
    if getattr(package, "__version__", None) != version(
        project_config.distribution_name
    ):
        msg = "Installed package version does not match distribution metadata."
        raise RuntimeError(msg)

    exported_names = list(getattr(package, "__all__", []))
    if not exported_names:
        msg = "Package __all__ must not be empty."
        raise RuntimeError(msg)
    missing_attributes = [name for name in exported_names if not hasattr(package, name)]
    if missing_attributes:
        msg = f"Missing exported attributes: {sorted(missing_attributes)}"
        raise RuntimeError(msg)

    print(f"Installed artifact smoke passed: {module_path}")


if __name__ == "__main__":
    main()
