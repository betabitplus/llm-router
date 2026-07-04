"""Shared project-tooling config loaded from `pyproject.toml`.

Why:
    Keeps repo-local tooling on the standard Python config file instead of a
    separate custom manifest while still exposing a small typed helper for
    repeated package and environment naming rules.

When to use:
    Import from repo-local scripts and shared test support when behavior
    depends on the repo's primary package, package list, or env-var prefix.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_PYPROJECT_FILE_NAME = "pyproject.toml"
_TOOL_TABLE = "py_lib_starter"


@dataclass(frozen=True, slots=True)
class ProjectToolingConfig:
    """Typed repo-tooling values loaded from `pyproject.toml`."""

    distribution_name: str
    primary_package: str
    package_names: tuple[str, ...]
    env_prefix: str

    def __post_init__(self) -> None:
        """Reject empty or internally inconsistent config values."""
        if not self.distribution_name:
            msg = "pyproject.toml [project].name must be a non-empty string."
            raise ValueError(msg)
        if not self.package_names:
            msg = (
                f"pyproject.toml [tool.{_TOOL_TABLE}].package_names must contain "
                "at least one package."
            )
            raise ValueError(msg)
        if self.primary_package not in self.package_names:
            msg = (
                f"pyproject.toml [tool.{_TOOL_TABLE}].primary_package must appear "
                "in package_names."
            )
            raise ValueError(msg)

    def env_var(self, suffix: str) -> str:
        """Return one repo-scoped environment variable name."""
        return f"{self.env_prefix}_{suffix}"

    @property
    def env_file_var(self) -> str:
        """Return the shared dotenv override variable for this repo."""
        return self.env_var("ENV_FILE")

    @property
    def record_vcr_var(self) -> str:
        """Return the standalone VCR-recording toggle variable for this repo."""
        return self.env_var("RECORD_VCR")

    @property
    def multipart_signature_prefix(self) -> bytes:
        """Return the VCR multipart signature prefix for this repo."""
        return f"{self.env_prefix}_MULTIPART_SIGNATURE:".encode("ascii")

    @property
    def public_contract_forbidden_prefixes(self) -> tuple[str, ...]:
        """Return private-core prefixes public-contract tests may not reference."""
        return tuple(f"{package_name}._internal" for package_name in self.package_names)

    def public_contract_checked_dirs(
        self,
        *,
        repo_root: Path | None = None,
    ) -> tuple[Path, ...]:
        """Return test trees checked for forbidden private-core references."""
        root = get_repo_root() if repo_root is None else repo_root
        checked_dirs: list[Path] = []
        for package_name in self.package_names:
            checked_dirs.extend(
                [
                    root / "tests" / package_name / "e2e",
                    root
                    / "tests"
                    / package_name
                    / "property_based"
                    / "public_contract",
                    root / "tests" / package_name / "support",
                ]
            )
        checked_dirs.append(root / "tests" / "support")
        return tuple(checked_dirs)


def get_repo_root() -> Path:
    """Return the repository root directory."""
    return _pyproject_path().parent


@lru_cache(maxsize=1)
def get_project_tooling_config() -> ProjectToolingConfig:
    """Load and cache the shared repo-tooling config."""
    with _pyproject_path().open("rb") as pyproject_file:
        raw_pyproject = tomllib.load(pyproject_file)

    project = _require_table(raw_pyproject, "project")
    tool = _require_table(raw_pyproject, "tool")
    tooling = _require_table(tool, _TOOL_TABLE)
    return ProjectToolingConfig(
        distribution_name=_require_string(project, "name"),
        primary_package=_require_string(tooling, "primary_package"),
        package_names=_normalize_package_names(tooling.get("package_names")),
        env_prefix=_require_string(tooling, "env_prefix"),
    )


@lru_cache(maxsize=1)
def _pyproject_path() -> Path:
    """Return the repo `pyproject.toml` path by walking upward from this module."""
    for candidate_root in Path(__file__).resolve().parents:
        candidate_path = candidate_root / _PYPROJECT_FILE_NAME
        if candidate_path.is_file():
            return candidate_path

    msg = f"Could not find {_PYPROJECT_FILE_NAME} above {__file__}."
    raise FileNotFoundError(msg)


def _normalize_package_names(value: object) -> tuple[str, ...]:
    """Return normalized package names from a TOML string array."""
    return _normalize_string_tuple(value, field_name="package_names")


def _normalize_string_tuple(value: object, *, field_name: str) -> tuple[str, ...]:
    """Return normalized non-empty strings from a TOML string array."""
    if not isinstance(value, list):
        msg = f"pyproject.toml [tool.{_TOOL_TABLE}].{field_name} must be a list."
        raise TypeError(msg)

    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            msg = (
                f"pyproject.toml [tool.{_TOOL_TABLE}].{field_name} items must be "
                "non-empty strings."
            )
            raise ValueError(msg)
        normalized.append(item.strip())
    return tuple(dict.fromkeys(normalized))


def _require_table(raw_config: dict[str, object], key: str) -> dict[str, object]:
    """Return one required TOML table."""
    value = raw_config.get(key)
    if not isinstance(value, dict):
        msg = f"pyproject.toml must define a [{key}] table."
        raise TypeError(msg)
    return value


def _require_string(table: dict[str, object], key: str) -> str:
    """Return one required non-empty string from a TOML table."""
    value = table.get(key)
    if not isinstance(value, str) or not value.strip():
        msg = f"pyproject.toml field {key!r} must be a non-empty string."
        raise ValueError(msg)
    return value.strip()
