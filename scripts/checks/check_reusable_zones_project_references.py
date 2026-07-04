"""Reject project-specific references inside reusable support zones.

Why:
    `tests/support/` and `scripts/_shared/` are intended to stay copyable
    across future repositories. They must not import or describe the current
    product package, project-specific test tree, or workbench tree.

How:
    Parse reusable-zone Python files and fail on direct imports or string
    literals that mention the current project's package-specific names.
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT_STR = str(REPO_ROOT)
if REPO_ROOT_STR not in sys.path:
    sys.path.insert(0, REPO_ROOT_STR)


@dataclass(frozen=True, slots=True)
class Violation:
    """One project-specific reference found in a reusable-zone Python file."""

    path: Path
    line: int
    kind: str
    value: str


class ReusableZoneReferenceVisitor(ast.NodeVisitor):
    """Collect project-specific imports and strings from one syntax tree."""

    def __init__(
        self,
        path: Path,
        *,
        forbidden_module_prefixes: tuple[str, ...],
        forbidden_string_fragments: tuple[str, ...],
    ) -> None:
        self._path = path
        self._forbidden_module_prefixes = forbidden_module_prefixes
        self._forbidden_string_fragments = forbidden_string_fragments
        self.violations: list[Violation] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if _is_forbidden_module_reference(
                alias.name,
                forbidden_module_prefixes=self._forbidden_module_prefixes,
            ):
                self.violations.append(
                    Violation(
                        path=self._path,
                        line=node.lineno,
                        kind="import",
                        value=alias.name,
                    )
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module_name = node.module
        if isinstance(module_name, str) and _is_forbidden_module_reference(
            module_name,
            forbidden_module_prefixes=self._forbidden_module_prefixes,
        ):
            self.violations.append(
                Violation(
                    path=self._path,
                    line=node.lineno,
                    kind="from-import",
                    value=module_name,
                )
            )
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        if isinstance(node.value, str) and _contains_forbidden_string_fragment(
            node.value,
            forbidden_string_fragments=self._forbidden_string_fragments,
        ):
            self.violations.append(
                Violation(
                    path=self._path,
                    line=node.lineno,
                    kind="string-reference",
                    value=node.value,
                )
            )
        self.generic_visit(node)


def main() -> int:
    """Return a failing exit code when reusable zones mention project code."""
    checked_dirs, forbidden_module_prefixes, forbidden_string_fragments = (
        _reusable_zone_check_config()
    )

    violations: list[Violation] = []
    for checked_dir in checked_dirs:
        violations.extend(
            _check_tree(
                checked_dir,
                forbidden_module_prefixes=forbidden_module_prefixes,
                forbidden_string_fragments=forbidden_string_fragments,
            )
        )

    if not violations:
        return 0

    print("Project-specific references found in reusable support zones:")
    for violation in sorted(violations, key=_violation_sort_key):
        relative_path = violation.path.relative_to(REPO_ROOT)
        print(
            f"- {relative_path}:{violation.line}: {violation.kind} -> {violation.value}"
        )
    return 1


def _check_tree(
    root: Path,
    *,
    forbidden_module_prefixes: tuple[str, ...],
    forbidden_string_fragments: tuple[str, ...],
) -> list[Violation]:
    """Return all project-specific references under one reusable-zone tree."""
    if not root.is_dir():
        return []

    violations: list[Violation] = []
    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        visitor = ReusableZoneReferenceVisitor(
            path,
            forbidden_module_prefixes=forbidden_module_prefixes,
            forbidden_string_fragments=forbidden_string_fragments,
        )
        visitor.visit(tree)
        violations.extend(visitor.violations)
    return violations


def _is_forbidden_module_reference(
    value: str,
    *,
    forbidden_module_prefixes: tuple[str, ...],
) -> bool:
    """Return whether one module reference points at a forbidden project prefix."""
    return any(
        value == prefix or value.startswith(f"{prefix}.")
        for prefix in forbidden_module_prefixes
    )


def _contains_forbidden_string_fragment(
    value: str,
    *,
    forbidden_string_fragments: tuple[str, ...],
) -> bool:
    """Return whether one string literal mentions a forbidden project fragment."""
    return any(fragment in value for fragment in forbidden_string_fragments)


def _violation_sort_key(violation: Violation) -> tuple[str, int, str]:
    """Keep failure output deterministic."""
    return (str(violation.path), violation.line, violation.value)


def _reusable_zone_check_config() -> tuple[
    tuple[Path, ...],
    tuple[str, ...],
    tuple[str, ...],
]:
    """Return reusable-zone roots and forbidden project references."""
    from scripts._shared.project_config import get_project_tooling_config

    project_config = get_project_tooling_config()
    package_names = project_config.package_names

    forbidden_module_prefixes = tuple(
        dict.fromkeys(
            [
                *package_names,
                *(f"tests.{package_name}" for package_name in package_names),
                *(f"workbench.{package_name}" for package_name in package_names),
            ]
        )
    )
    forbidden_string_fragments = tuple(
        dict.fromkeys(
            [
                *package_names,
                *(f"tests.{package_name}" for package_name in package_names),
                *(f"workbench.{package_name}" for package_name in package_names),
            ]
        )
    )
    checked_dirs = (
        REPO_ROOT / "tests" / "support",
        REPO_ROOT / "scripts" / "_shared",
    )
    return checked_dirs, forbidden_module_prefixes, forbidden_string_fragments


if __name__ == "__main__":
    raise SystemExit(main())
