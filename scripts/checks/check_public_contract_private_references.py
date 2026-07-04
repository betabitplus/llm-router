"""Reject private-core references in public-contract verification modules.

Why:
    Import Linter only sees import graph edges. Public-contract test helpers
    also need protection against runtime module-name references such as
    `sys.modules[...]` and `importlib.import_module(...)`.

How:
    Parse the public-contract test trees and fail on direct imports or string
    literals that point at forbidden private module prefixes.
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
    """One forbidden private-core reference found in a Python file."""

    path: Path
    line: int
    kind: str
    value: str


class PrivateReferenceVisitor(ast.NodeVisitor):
    """Collect direct and runtime private-core references from one syntax tree."""

    def __init__(self, path: Path, *, forbidden_prefixes: tuple[str, ...]) -> None:
        self._path = path
        self._forbidden_prefixes = forbidden_prefixes
        self.violations: list[Violation] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if _is_forbidden_reference(
                alias.name,
                forbidden_prefixes=self._forbidden_prefixes,
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
        if isinstance(module_name, str) and _is_forbidden_reference(
            module_name,
            forbidden_prefixes=self._forbidden_prefixes,
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
        if isinstance(node.value, str) and _is_forbidden_reference(
            node.value,
            forbidden_prefixes=self._forbidden_prefixes,
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
    """Return a failing exit code when public-contract modules reference `_internal`."""
    checked_dirs, forbidden_prefixes = _manifest_check_config()

    violations: list[Violation] = []
    for checked_dir in checked_dirs:
        violations.extend(
            _check_tree(checked_dir, forbidden_prefixes=forbidden_prefixes)
        )

    if not violations:
        return 0

    print("Forbidden private-core references found in public-contract modules:")
    for violation in sorted(violations, key=_violation_sort_key):
        relative_path = violation.path.relative_to(REPO_ROOT)
        print(
            f"- {relative_path}:{violation.line}: {violation.kind} -> {violation.value}"
        )
    return 1


def _check_tree(
    root: Path,
    *,
    forbidden_prefixes: tuple[str, ...],
) -> list[Violation]:
    """Return all forbidden private-core references under one checked tree."""
    if not root.is_dir():
        return []

    violations: list[Violation] = []
    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        visitor = PrivateReferenceVisitor(path, forbidden_prefixes=forbidden_prefixes)
        visitor.visit(tree)
        violations.extend(visitor.violations)
    return violations


def _is_forbidden_reference(value: str, *, forbidden_prefixes: tuple[str, ...]) -> bool:
    """Return whether one module reference points at a forbidden private prefix."""
    return any(
        value == prefix or value.startswith(f"{prefix}.")
        for prefix in forbidden_prefixes
    )


def _violation_sort_key(violation: Violation) -> tuple[str, int, str]:
    """Keep failure output deterministic."""
    return (str(violation.path), violation.line, violation.value)


def _manifest_check_config() -> tuple[tuple[Path, ...], tuple[str, ...]]:
    """Return checked dirs and forbidden prefixes from the repo manifest."""
    from scripts._shared.project_config import get_project_tooling_config

    config = get_project_tooling_config()
    return (
        config.public_contract_checked_dirs(repo_root=REPO_ROOT),
        config.public_contract_forbidden_prefixes,
    )


if __name__ == "__main__":
    raise SystemExit(main())
