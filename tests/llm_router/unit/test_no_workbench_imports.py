from __future__ import annotations

import ast
from pathlib import Path


def _imports_workbench(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "workbench" or alias.name.startswith("workbench."):
                    return True
        if (
            isinstance(node, ast.ImportFrom)
            and node.module is not None
            and (node.module == "workbench" or node.module.startswith("workbench."))
        ):
            return True
    return False


def test_internal_source_files_do_not_import_workbench() -> None:
    internal_root = Path("src/llm_router/_internal")
    offenders = sorted(
        str(path) for path in internal_root.rglob("*.py") if _imports_workbench(path)
    )

    assert offenders == []
